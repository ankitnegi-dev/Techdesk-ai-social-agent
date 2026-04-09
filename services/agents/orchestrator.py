"""
OrchestratorAgent — entry point of the LangGraph.
Classifies the incoming signal and routes to the right specialist agent.
"""
import json
import logging
from groq import Groq
from services.agents.state import AgentState
from shared.config import get_settings
from shared.models import IntentClass

settings = get_settings()
log = logging.getLogger("orchestrator")
client = Groq(api_key=settings.groq_api_key)

CRISIS_INTENTS = {IntentClass.CRISIS_SIGNAL.value}
ENGAGEMENT_INTENTS = {
    IntentClass.COMPLAINT.value,
    IntentClass.PRAISE.value,
    IntentClass.QUESTION.value,
    IntentClass.NEUTRAL_MENTION.value,
    IntentClass.COMPETITOR_ATTACK.value,
}
CONTENT_INTENTS = {IntentClass.VIRAL_OPPORTUNITY.value}

def orchestrator_node(state: AgentState) -> AgentState:
    """Classify intent and decide which agent handles this signal."""
    signal = state.signal or {}
    content = signal.get("content", "")

    log.info(f"[Orchestrator] Routing signal: {content[:60]}")

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a social media signal classifier. Respond ONLY with a JSON object."},
            {"role": "user", "content": f"""Classify this social media post:
"{content}"

Respond with ONLY this JSON, no other text:
{{"intent": "complaint|praise|question|neutral_mention|competitor_attack|crisis_signal|viral_opportunity",
  "sentiment": <float -1.0 to 1.0>,
  "is_crisis": <true|false>,
  "confidence": <float 0.0 to 1.0>}}"""}
        ],
        max_tokens=100,
        temperature=0.1,
    )

    try:
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        data = json.loads(raw)
        intent = str(data.get("intent", "neutral_mention"))
        sentiment = float(data.get("sentiment", 0.0))
        is_crisis = bool(data.get("is_crisis", False))
    except Exception as e:
        log.warning(f"Classification parse error: {e} — defaulting to neutral")
        intent = "neutral_mention"
        sentiment = 0.0
        is_crisis = False

    # Route decision
    if is_crisis or intent in CRISIS_INTENTS:
        route = "crisis"
    elif intent in CONTENT_INTENTS:
        route = "content_creator"
    else:
        route = "engagement"

    log.info(f"[Orchestrator] intent={intent} sentiment={sentiment:+.2f} → {route}")

    return AgentState(
        **{**state.model_dump(),
           "intent": intent,
           "sentiment": sentiment,
           "is_crisis": is_crisis,
           "route_to": route}
    )

def route_signal(state: AgentState) -> str:
    """LangGraph conditional edge — returns next node name."""
    return state.route_to
