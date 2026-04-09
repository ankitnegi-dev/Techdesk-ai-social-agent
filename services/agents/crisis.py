"""
CrisisAgent — activates on negative sentiment spikes.
Pauses proactive posting and escalates to HITL immediately.
"""
import logging
from services.agents.state import AgentState

log = logging.getLogger("crisis")

def crisis_node(state: AgentState) -> AgentState:
    signal = state.signal or {}
    content = signal.get("content", "")
    author = signal.get("author_username", "unknown")

    log.warning(f"[CRISIS] Escalating signal from @{author}: {content[:80]}")

    draft = f"[CRISIS ESCALATION] From @{author}: {content}"
    return AgentState(
        **{**state.model_dump(),
           "draft_content": draft,
           "action_type": "escalate",
           "final": True}
    )
