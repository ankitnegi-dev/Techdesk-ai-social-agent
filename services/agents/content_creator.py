"""
ContentCreatorAgent — creates proactive posts for viral opportunities.
"""
import logging
from groq import Groq
from services.agents.state import AgentState
from shared.config import get_settings

settings = get_settings()
log = logging.getLogger("content_creator")
client = Groq(api_key=settings.groq_api_key)

def content_creator_node(state: AgentState) -> AgentState:
    signal = state.signal or {}
    persona = state.persona or {}
    content = signal.get("content", "")
    name = persona.get("display_name", "our brand")
    tone = persona.get("tone_primary", "friendly")

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": f"You are a creative social media manager for {name}. Tone: {tone}. Write engaging posts under 280 characters that add unique value."},
            {"role": "user", "content": f"This is trending: \"{content}\"\n\nCreate an original post that adds a unique angle from {name}'s perspective. Reply only with the tweet text."}
        ],
        max_tokens=150,
        temperature=0.8,
    )

    draft = response.choices[0].message.content.strip().strip('"')
    log.info(f"[ContentCreator] Draft: {draft[:100]}")

    return AgentState(**{**state.model_dump(), "draft_content": draft, "action_type": "post"})
