from typing import TypedDict, Any, Optional
from app.models.agent import AgentTraceEvent


class PlannerState(TypedDict):
    session_id: str
    raw_input: str

    # Goal parsing output
    trip_goal: Optional[dict]

    # Worker outputs
    worker_results: dict           # keyed by worker name

    # Synthesis outputs
    itinerary_days: list[dict]
    budget_breakdown: Optional[dict]

    # Critique
    critique_result: Optional[dict]
    critique_iteration: int

    # Post-approval
    constraint_checks: list[dict]
    decision_explanations: list[dict]

    # Trace
    trace_events: list[dict]

    # Final
    error: Optional[str]
    is_complete: bool
