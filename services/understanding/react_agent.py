import logging
import json
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from groq import Groq
from shared.models import (
    SocialSignal, AgentAction, ActionType,
    IntentClass, SignalClassification, PersonaConfig,
)
from shared.config import get_settings

settings = get_settings()
log = logging.getLogger("understanding")
client = Groq(api_key=settings.groq_api_key)

GROQ_MODEL = "llama-3.3-70b-versatile"

STRATEGY_MAP = {
    IntentClass.COMPLAINT:         "Lead with empathy. Acknowledge frustration. Offer to help. Never argue. End with a clear next step.",
    IntentClass.PRAISE:            "Thank them genuinely. Warm but not over the top. Keep it short.",
    IntentClass.QUESTION:          "Answer directly and accurately. If uncertain, say so. Offer to follow up.",
    IntentClass.NEUTRAL_MENTION:   "Acknowledge warmly. Brief. No hard sell.",
    IntentClass.COMPETITOR_ATTACK: "Stay factual, calm, non-aggressive. Focus on your own strengths only.",
    IntentClass.CRISIS_SIGNAL:     "ESCALATE TO HUMAN IMMEDIATELY. Do not auto-reply.",
    IntentClass.VIRAL_OPPORTUNITY: "Add a unique angle or insight. Do not just join the bandwagon.",
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "classify_intent",
            "description": "Classify the intent and sentiment of a social media post.",
            "parameters": {
                "type": "object",
                "properties": {
                    "intent": {
                        "type": "string",
                        "enum": [i.value for i in IntentClass],
                    },
                    "sentiment_score": {"type": "number"},
                    "confidence":      {"type": "number"},
                    "entities":        {"type": "array", "items": {"type": "string"}},
                    "is_crisis":       {"type": "boolean"},
                },
                "required": ["intent", "sentiment_score", "confidence", "is_crisis"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": "Route to human review. Use for crisis, sensitive topics, or low confidence.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason":  {"type": "string"},
                    "urgency": {"type": "string", "enum": ["urgent", "normal"]},
                },
                "required": ["reason", "urgency"],
            },
        },
    },
]

def build_system_prompt(persona: PersonaConfig) -> str:
    examples = "\n".join(f'  - "{ex}"' for ex in persona.voice_examples[:5])
    return f"""You are a social media agent managing the {persona.display_name} account.

PERSONA:
- Tone: {persona.tone_primary}, {persona.tone_secondary}
- Engage with: {", ".join(persona.topics) or "general brand topics"}
- Never mention: {", ".join(persona.avoid_topics) or "none"}
- Approved hashtags: {", ".join(persona.approved_hashtags) or "none"}

VOICE EXAMPLES:
{examples or "  - Be helpful, concise, and on-brand"}

RULES:
1. Never make promises you cannot keep
2. Never mention competitors negatively
3. Keep replies under 280 characters for Twitter
4. If unsure, escalate — do not guess on sensitive topics
5. Always call classify_intent first, then draft a reply
"""

def _coerce_classify_args(args: dict) -> dict:
    """Force correct types — Llama sometimes returns numbers as strings."""
    return {
        "intent":          str(args.get("intent", "neutral_mention")),
        "sentiment_score": float(args.get("sentiment_score", 0.0)),
        "confidence":      float(args.get("confidence", 0.5)),
        "entities":        list(args.get("entities", [])),
        "is_crisis":       str(args.get("is_crisis", "false")).lower() == "true"
                           if isinstance(args.get("is_crisis"), str)
                           else bool(args.get("is_crisis", False)),
    }

async def process_signal(signal: SocialSignal, persona: PersonaConfig) -> AgentAction:
    log.info(f"Processing @{signal.author_username}: {signal.content[:80]}")

    messages = [
        {"role": "system", "content": build_system_prompt(persona)},
        {
            "role": "user",
            "content": (
                f"New social signal:\nPlatform: {signal.platform.value}\n"
                f"Author: @{signal.author_username}\nContent: {signal.content}\n\n"
                "Call classify_intent first, then draft a reply."
            )
        }
    ]

    classification = None
    draft_content = ""
    action_type = ActionType.REPLY

    for iteration in range(5):
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            max_tokens=1024,
        )

        msg = response.choices[0].message
        messages.append({
            "role": "assistant",
            "content": msg.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    }
                }
                for tc in (msg.tool_calls or [])
            ]
        })

        if not msg.tool_calls:
            draft_content = (msg.content or "").strip()
            break

        tool_results = []
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)

            if tc.function.name == "classify_intent":
                safe_args = _coerce_classify_args(args)
                classification = SignalClassification(**safe_args)
                if classification.is_crisis or classification.intent == IntentClass.CRISIS_SIGNAL:
                    action_type = ActionType.ESCALATE
                    draft_content = f"[CRISIS] {signal.content}"
                strategy = STRATEGY_MAP.get(
                    IntentClass(safe_args["intent"]), "Respond helpfully."
                )
                result = {
                    "status": "classified",
                    "strategy": strategy,
                    "instruction": f"Now draft a reply using this strategy: {strategy}",
                }

            elif tc.function.name == "escalate_to_human":
                action_type = ActionType.ESCALATE
                draft_content = f"[ESCALATED: {args.get('reason')}] {signal.content}"
                result = {"status": "escalated"}
            else:
                result = {"status": "unknown"}

            tool_results.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(result),
            })

        messages.extend(tool_results)

        if action_type == ActionType.ESCALATE:
            break

    if classification:
        signal.classification = classification

    log.info(f"Draft [{action_type.value}]: {draft_content[:120]}")
    return AgentAction(
        signal_id=signal.id,
        agent_id="engagement_agent_v1",
        action_type=action_type,
        draft_content=draft_content,
    )
