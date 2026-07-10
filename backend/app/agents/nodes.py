"""
All graph nodes — fully implemented through Milestone 4.
"""
import asyncio
import logging
import time
from app.agents.state import PlannerState

logger = logging.getLogger(__name__)


def _clean_error(e: Exception) -> str:
    """Return a short, human-readable error string — strips proto/gRPC boilerplate."""
    msg = str(e)
    # Google API errors: first line before the proto block is enough
    first_line = msg.split("\n")[0].split("[")[0].strip().rstrip(".")
    if "429" in first_line or "RESOURCE_EXHAUSTED" in first_line or "quota" in first_line.lower():
        return "Gemini API quota exceeded — try again tomorrow or use a different API key"
    if "403" in first_line or "PERMISSION_DENIED" in first_line:
        return "Gemini API key invalid or permission denied"
    # Truncate anything still too long
    return first_line[:120] if len(first_line) > 120 else first_line


def _trace(state: PlannerState, agent: str, status: str, message: str, **kwargs) -> dict:
    event = {
        "agent": agent,
        "status": status,
        "message": message,
        "timestamp_ms": int(time.time() * 1000),
        **kwargs,
    }
    return {
        "trace_events": state.get("trace_events", []) + [event]
    }


# ── Goal Parser (Milestone 4) ─────────────────────────────────────────────────

def parse_goal_node(state: PlannerState) -> dict:
    from app.agents.goal_parser import parse_goal
    raw = state.get("raw_input", "")
    try:
        trip_goal = parse_goal(raw)
        return {
            **_trace(state, "GoalParser", "completed",
                     f"Parsed: {trip_goal['destination']}, "
                     f"{trip_goal['duration_days']} days, "
                     f"INR {trip_goal['budget_inr']:,.0f}, "
                     f"interests: {', '.join(trip_goal.get('interests', []))}"),
            "trip_goal": trip_goal,
        }
    except Exception as e:
        logger.exception("Goal parsing failed")
        return {
            **_trace(state, "GoalParser", "failed", f"Parsing error: {_clean_error(e)}"),
            "error": _clean_error(e),
        }


# ── Real: dispatch_workers (Milestone 3) ─────────────────────────────────────

def dispatch_workers_node(state: PlannerState) -> dict:
    """
    Run all 6 research workers in parallel.
    LangGraph nodes are sync — we run the async workers via asyncio.
    """
    from app.agents.workers import run_all_workers

    trip_goal = state.get("trip_goal") or {}

    start_trace = {
        "agent": "WorkerDispatcher",
        "status": "started",
        "message": f"Dispatching 6 workers in parallel for {trip_goal.get('destination', 'destination')}",
        "timestamp_ms": int(time.time() * 1000),
    }

    # Run async workers from sync node
    worker_results, worker_traces = asyncio.run(run_all_workers(trip_goal))

    done_trace = {
        "agent": "WorkerDispatcher",
        "status": "completed",
        "message": f"All workers complete — "
                   f"{sum(1 for w in worker_results.values() if w['success'])}/6 succeeded",
        "timestamp_ms": int(time.time() * 1000),
    }

    existing = state.get("trace_events", [])
    return {
        "worker_results": worker_results,
        "trace_events": existing + [start_trace] + worker_traces + [done_trace],
    }


# ── PlanSynthesizer (Milestone 4) ────────────────────────────────────────────

def synthesize_plan_node(state: PlannerState) -> dict:
    from app.agents.synthesizer import synthesize_plan, compute_budget_breakdown

    iteration = state.get("critique_iteration", 0)
    trip_goal = state.get("trip_goal") or {}
    worker_results = state.get("worker_results", {})
    objections = (state.get("critique_result") or {}).get("objections", [])

    try:
        itinerary_days = synthesize_plan(trip_goal, worker_results, objections or None)
        budget_breakdown = compute_budget_breakdown(itinerary_days, trip_goal, worker_results)

        surplus = budget_breakdown.get("surplus_deficit_inr", 0)
        surplus_label = f"surplus INR {surplus:,.0f}" if surplus >= 0 else f"OVERRUN INR {abs(surplus):,.0f}"

        return {
            **_trace(state, "PlanSynthesizer", "completed",
                     f"Pass {iteration + 1}: {len(itinerary_days)} days planned, "
                     f"total INR {budget_breakdown.get('total_inr', 0):,.0f} — {surplus_label}"),
            "itinerary_days": itinerary_days,
            "budget_breakdown": budget_breakdown,
            "critique_iteration": iteration + 1,
        }
    except Exception as e:
        logger.exception("Synthesis failed")
        return {
            **_trace(state, "PlanSynthesizer", "failed", f"Synthesis error: {_clean_error(e)}"),
            "itinerary_days": [],
            "budget_breakdown": {},
            "critique_iteration": iteration + 1,
            "error": _clean_error(e),
        }


# ── CritiqueOptimizer (Milestone 4) ──────────────────────────────────────────

def critique_plan_node(state: PlannerState) -> dict:
    from app.agents.critic import critique_plan

    trip_goal = state.get("trip_goal") or {}
    itinerary_days = state.get("itinerary_days", [])
    budget_breakdown = state.get("budget_breakdown") or {}
    iteration = state.get("critique_iteration", 1)

    if not itinerary_days:
        return {
            **_trace(state, "CritiqueOptimizer", "failed",
                     "No itinerary to critique — auto-approving"),
            "critique_result": {"approved": True, "objections": [], "iteration": iteration},
        }

    try:
        result = critique_plan(trip_goal, itinerary_days, budget_breakdown, iteration)
        status = "approved" if result.get("approved") else "rejected"
        objections = result.get("objections", [])

        message = (
            f"Pass {iteration}: Plan {status} (score {result.get('score', '?')}/10)"
            if result.get("approved")
            else f"Pass {iteration}: Rejected — {'; '.join(objections[:2])}"
        )

        return {
            **_trace(state, "CritiqueOptimizer", "completed", message),
            "critique_result": result,
        }
    except Exception as e:
        logger.exception("Critique failed")
        return {
            **_trace(state, "CritiqueOptimizer", "failed", f"Critique error: {_clean_error(e)} — auto-approving"),
            "critique_result": {"approved": True, "objections": [], "iteration": iteration},
        }


# ── Decision Explainer (Milestone 4) ─────────────────────────────────────────

def generate_explanations_node(state: PlannerState) -> dict:
    from app.agents.explainer import generate_explanations
    from app.agents.constraint_checker import check_constraints

    trip_goal = state.get("trip_goal") or {}
    itinerary_days = state.get("itinerary_days", [])
    budget_breakdown = state.get("budget_breakdown") or {}
    worker_results = state.get("worker_results", {})

    # Run constraint checker (pure Python — no LLM)
    constraint_checks = check_constraints(trip_goal, itinerary_days, budget_breakdown, worker_results)
    passed = sum(1 for c in constraint_checks if c["status"] == "passed")
    failed = sum(1 for c in constraint_checks if c["status"] == "failed")

    # Generate explanations via Gemini
    try:
        explanations = generate_explanations(trip_goal, itinerary_days, budget_breakdown)
    except Exception as e:
        logger.exception("Explanation generation failed")
        explanations = []

    return {
        **_trace(state, "DecisionExplainer", "completed",
                 f"Constraints: {passed} passed, {failed} failed | "
                 f"{len(explanations)} decision explanations generated"),
        "constraint_checks": constraint_checks,
        "decision_explanations": explanations,
    }


# ── Finalize (Milestone 3+4) ──────────────────────────────────────────────────

def finalize_plan_node(state: PlannerState) -> dict:
    itinerary_days = state.get("itinerary_days", [])
    budget = state.get("budget_breakdown") or {}
    critique = state.get("critique_result") or {}

    return {
        **_trace(state, "Orchestrator", "completed",
                 f"Complete — {len(itinerary_days)} days, "
                 f"INR {budget.get('total_inr', 0):,.0f} total, "
                 f"critique score {critique.get('score', 'N/A')}/10"),
        "is_complete": True,
    }
