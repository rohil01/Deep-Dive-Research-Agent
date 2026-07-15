"""Graph construction and the public `run_research` entry point."""
import logging

from langgraph.graph import END, StateGraph

from .config import get_settings
from .nodes import critic_node, planner_node, researcher_node, writer_node
from .state import ResearchState

logger = logging.getLogger(__name__)


def should_continue_research(state: ResearchState) -> str:
    """Route from critic: loop back to planner or proceed to writer."""
    if state.get("should_continue", False):
        logger.info("Looping back to planner for additional research...")
        return "planner"
    logger.info("Proceeding to writer...")
    return "writer"


def build_graph():
    """Constructs and compiles the LangGraph state machine."""
    workflow = StateGraph(ResearchState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("critic", critic_node)
    workflow.add_node("writer", writer_node)

    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "researcher")
    workflow.add_edge("researcher", "critic")
    workflow.add_conditional_edges(
        "critic",
        should_continue_research,
        {"planner": "planner", "writer": "writer"},
    )
    workflow.add_edge("writer", END)

    return workflow.compile()


def run_research(query: str) -> str:
    """Execute the research agent for a query and return the final report."""
    get_settings().validate_keys()

    graph = build_graph()

    initial_state: ResearchState = {
        "query": query,
        "plan": [],
        "pending_questions": [],
        "notes": [],
        "iteration": 0,
        "critique": "",
        "final_report": "",
        "should_continue": True,
    }

    final_state = graph.invoke(initial_state)
    return final_state["final_report"]
