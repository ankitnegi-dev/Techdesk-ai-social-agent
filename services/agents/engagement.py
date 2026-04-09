"""
EngagementAgent — drafts replies to incoming mentions using RAG context.
"""
import asyncio
import logging
from groq import Groq
from services.agents.state import AgentState
from shared.config import get_settings

settings = get_settings()
log = logging.getLogger("engagement")
client = Groq(api_key=settings.groq_api_key)

def engagement_node(state: AgentState) -> AgentState:
    signal = state.signal or {}
    persona = state.persona or {}
    content = signal.get("content", "")
    author = signal.get("author_username", "user")
    intent = state.intent or "neutral_mention"

    # Build RAG context string
    rag_context = ""
    if state.rag_context:
        chunks = "\n".join([
            f"- {c['title']}: {c['content']}"
            for c in state.rag_context[:3]
        ])
        rag_context = f"\n\nRELEVANT KNOWLEDGE BASE:\n{chunks}"

    strategy_map = {
        "complaint": "Lead with empathy. Acknowledge the frustration specifically. Offer concrete help. End with a clear next step.",
        "praise": "Thank them warmly and genuinely. Keep it short. Do not oversell.",
        "question": "Answer directly and accurately using the knowledge base. If unsure, offer to follow up.",
        "neutral_mention": "Acknowledge warmly and briefly. No hard sell.",
        "competitor_attack": "Stay calm and factual. Focus only on your strengths. Never attack the competitor.",
    }
    strategy = strategy_map.get(intent, "Respond helpfully and on-brand.")

    tone = persona.get("tone_primary", "friendly")
    name = persona.get("display_name", "our brand")
    examples = persona.get("voice_examples", [])
    example_str = "\n".join(f'  - "{e}"' for e in examples[:3])

    system = f"""You are the social media agent for {name}.
Tone: {tone}
Strategy: {strategy}
Voice examples:\n{example_str}
Rules: Under 280 characters. Never make promises. Never mention competitors negatively.{rag_context}"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"Draft a reply to @{author} who said: \"{content}\"\n\nReply only with the tweet text, nothing else."}
        ],
        max_tokens=150,
        temperature=0.7,
    )

    draft = response.choices[0].message.content.strip().strip('"')
    log.info(f"[Engagement] Draft: {draft[:100]}")

    return AgentState(**{**state.model_dump(), "draft_content": draft, "action_type": "reply"})
