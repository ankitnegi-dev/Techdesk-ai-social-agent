from typing import Optional, Annotated
from langgraph.graph.message import add_messages
from shared.models import SocialSignal, AgentAction, PersonaConfig
from pydantic import BaseModel
import operator

class AgentState(BaseModel):
    signal: Optional[dict] = None
    persona: Optional[dict] = None
    intent: Optional[str] = None
    sentiment: Optional[float] = None
    is_crisis: bool = False
    rag_context: list[dict] = []
    draft_content: str = ""
    action_type: str = "reply"
    safety_passed: bool = False
    route_to: str = "engagement"
    iteration: int = 0
    final: bool = False

    class Config:
        arbitrary_types_allowed = True
