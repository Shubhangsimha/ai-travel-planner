import logging
from langgraph.graph import StateGraph, END
from app.agents.state import PlannerState
from app.agents import nodes

logger = logging.getLogger(__name__)

MAX_CRITIQUE_ITERATIONS = 3


def _should_continue_critique(state: PlannerState) -> str:
    critique = state.get("critique_result") or {}
    iteration = state.get("critique_iteration", 0)

    if iteration >= MAX_CRITIQUE_ITERATIONS:
        logger.info("Critique loop limit reached (%d) — forcing finalize", MAX_CRITIQUE_ITERATIONS)
        return "finalize"

    if critique.get("approved", False):
        return "finalize"

    return "synthesize"


def build_graph() -> StateGraph:
    graph = StateGraph(PlannerState)

    graph.add_node("parse_goal", nodes.parse_goal_node)
    graph.add_node("dispatch_workers", nodes.dispatch_workers_node)
    graph.add_node("synthesize_plan", nodes.synthesize_plan_node)
    graph.add_node("critique_plan", nodes.critique_plan_node)
    graph.add_node("generate_explanations", nodes.generate_explanations_node)
    graph.add_node("finalize_plan", nodes.finalize_plan_node)

    graph.set_entry_point("parse_goal")
    graph.add_edge("parse_goal", "dispatch_workers")
    graph.add_edge("dispatch_workers", "synthesize_plan")
    graph.add_edge("synthesize_plan", "critique_plan")

    graph.add_conditional_edges(
        "critique_plan",
        _should_continue_critique,
        {
            "synthesize": "synthesize_plan",
            "finalize": "generate_explanations",
        },
    )

    graph.add_edge("generate_explanations", "finalize_plan")
    graph.add_edge("finalize_plan", END)

    return graph.compile()


planner_graph = build_graph()
