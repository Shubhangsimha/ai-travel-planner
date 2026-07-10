import uuid
import asyncio
import logging
import time
from collections import defaultdict
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator

from app.core.session import create_session, stream_events, emit, close_session

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")

# Simple in-process rate limiter
_MAX_CONCURRENT = 5          # max simultaneous planning jobs
_MAX_PER_IP_PER_HOUR = 10    # max requests per IP per hour
_ip_timestamps: dict[str, list[float]] = defaultdict(list)


def _check_rate_limit(client_ip: str) -> None:
    now = time.time()
    window = now - 3600  # 1 hour window
    timestamps = [t for t in _ip_timestamps[client_ip] if t > window]
    _ip_timestamps[client_ip] = timestamps
    if len(timestamps) >= _MAX_PER_IP_PER_HOUR:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded — max {_MAX_PER_IP_PER_HOUR} planning requests per hour",
        )
    _ip_timestamps[client_ip].append(now)


class PlanRequest(BaseModel):
    raw_input: str

    @field_validator("raw_input")
    @classmethod
    def validate_input(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 20:
            raise ValueError("Please describe your trip in at least 20 characters")
        if len(v) > 2000:
            raise ValueError("Trip description must be under 2000 characters")
        return v


@router.post("/plan", status_code=202)
async def create_plan(request: PlanRequest, http_request: Request):
    from app.core.session import _queues
    if len(_queues) >= _MAX_CONCURRENT:
        raise HTTPException(
            status_code=503,
            detail="Server busy — too many planning jobs in progress. Please try again shortly.",
        )

    client_ip = http_request.client.host if http_request.client else "unknown"
    _check_rate_limit(client_ip)

    session_id = str(uuid.uuid4())
    create_session(session_id)
    asyncio.create_task(_run_planning(session_id, request.raw_input))
    return {"session_id": session_id}


@router.get("/stream/{session_id}")
async def stream_plan(session_id: str):
    return StreamingResponse(
        stream_events(session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _run_planning(session_id: str, raw_input: str) -> None:
    """
    Runs the LangGraph planner in a thread so the async event loop stays free.
    Streams each trace event to the SSE session as the graph produces them.
    """
    from app.agents.graph import planner_graph
    from app.agents.state import PlannerState

    initial_state: PlannerState = {
        "session_id": session_id,
        "raw_input": raw_input,
        "trip_goal": None,
        "worker_results": {},
        "itinerary_days": [],
        "budget_breakdown": None,
        "critique_result": None,
        "critique_iteration": 0,
        "constraint_checks": [],
        "decision_explanations": [],
        "trace_events": [],
        "error": None,
        "is_complete": False,
    }

    try:
        await emit(session_id, {
            "type": "trace",
            "agent": "Orchestrator",
            "status": "started",
            "message": "Planning pipeline started.",
        })

        # Run the sync LangGraph in a thread to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, planner_graph.invoke, initial_state
        )

        # Stream all trace events collected during the graph run
        for event in result.get("trace_events", []):
            await emit(session_id, {"type": "trace", **event})

        # Emit the final result payload
        await emit(session_id, {
            "type": "complete",
            "session_id": session_id,
            "trip_goal": result.get("trip_goal"),
            "worker_results": _sanitize_worker_results(result.get("worker_results", {})),
            "itinerary_days": result.get("itinerary_days", []),
            "budget_breakdown": result.get("budget_breakdown"),
            "constraint_checks": result.get("constraint_checks", []),
            "decision_explanations": result.get("decision_explanations", []),
        })

    except Exception as e:
        logger.exception("Planning pipeline error for session %s", session_id)
        await emit(session_id, {"type": "error", "message": str(e)})
    finally:
        await close_session(session_id)


def _sanitize_worker_results(worker_results: dict) -> dict:
    """Trim large raw data fields before sending to frontend."""
    sanitized = {}
    for name, result in worker_results.items():
        sanitized[name] = {
            "worker_name": name,
            "success": result.get("success"),
            "is_test_data": result.get("is_test_data", False),
            "error": result.get("error"),
            "summary": _worker_summary(name, result.get("data", {})),
        }
    return sanitized


def _worker_summary(name: str, data: dict) -> str:
    if name == "WeatherWorker":
        forecasts = data.get("forecasts", [])
        if forecasts:
            f = forecasts[0]
            return f"{len(forecasts)} days — {f.get('description', '')} {f.get('temp_max_c', '')}°C"
        return "No forecast data"
    if name == "FlightWorker":
        est = data.get("price_estimate", {})
        return f"Est. INR {est.get('estimated_price_inr', 0):,} | {len(data.get('routes', []))} routes found"
    if name == "HotelWorker":
        hotels = data.get("hotels", [])
        if hotels:
            return f"{len(hotels)} hotels — from INR {hotels[0].get('estimated_nightly_inr', 0):,}/night"
        return "No hotels found"
    if name == "CurrencyWorker":
        return f"1 INR = {data.get('rate', 0)} {data.get('to', '')} | Budget: {data.get('to', '')} {data.get('budget_converted', 0):,}"
    if name == "AttractionsWorker":
        return f"{len(data.get('attractions', []))} attractions found"
    if name == "RestaurantWorker":
        return f"{len(data.get('restaurants', []))} restaurants found"
    return "OK"
