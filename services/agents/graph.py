"""
LangGraph agent graph — wires all specialist agents together.
OrchestratorAgent routes to EngagementAgent, CrisisAgent, or ContentCreatorAgent.
"""
import logging
from langgraph.graph import StateGraph, END
from services.agents.state import AgentState
from services.agents.orchestrator import orchestrator_node, route_signal
from services.agents.engagement import engagement_node
from services.agents.crisis import crisis_node
from services.agents.content_creator import content_creator_node

log = logging.getLogger("graph")

def build_graph():
    graph = StateGraph(AgentState)

    # Add nodes
    graph.add_node("orchestrator",    orchestrator_node)
    graph.add_node("engagement",      engagement_node)
    graph.add_node("crisis",          crisis_node)
    graph.add_node("content_creator", content_creator_node)

    # Entry point
    graph.set_entry_point("orchestrator")

    # Conditional routing from orchestrator
    graph.add_conditional_edges(
        "orchestrator",
        route_signal,
        {
            "engagement":      "engagement",
            "crisis":          "crisis",
            "content_creator": "content_creator",
        }
    )

    # All specialist agents go to END
    graph.add_edge("engagement",      END)
    graph.add_edge("crisis",          END)
    graph.add_edge("content_creator", END)

    return graph.compile()

# Build once at import time
agent_graph = build_graph()
log.info("LangGraph agent graph compiled successfully")

async def run_graph(signal: dict, persona: dict, rag_context: list = []) -> dict:
    """Run the full agent graph for one signal. Returns final state."""
    initial_state = AgentState(
        signal=signal,
        persona=persona,
        rag_context=rag_context,
    )
    result = agent_graph.invoke(initial_state)
    return result
