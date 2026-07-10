from pydantic import BaseModel, Field
from typing import List, Optional, Any
from enum import Enum


class AgentStatus(str, Enum):
    started = "started"
    running = "running"
    completed = "completed"
    failed = "failed"


class AgentTraceEvent(BaseModel):
    agent_name: str
    status: AgentStatus
    message: str
    timestamp_ms: int = 0
    duration_ms: Optional[int] = None
    query_summary: Optional[str] = None
    result_summary: Optional[str] = None


class DecisionExplanation(BaseModel):
    title: str
    reasoning: str
    alternatives_considered: List[str] = Field(default_factory=list)
    constraint_satisfied: Optional[str] = None


class CritiqueResult(BaseModel):
    approved: bool
    objections: List[str] = Field(default_factory=list)
    iteration: int = 0


class PlannerState(BaseModel):
    session_id: str
    raw_input: str = ""
    trip_goal: Optional[Any] = None
    worker_results: List[Any] = Field(default_factory=list)
    itinerary_days: List[Any] = Field(default_factory=list)
    budget_breakdown: Optional[Any] = None
    constraint_checks: List[Any] = Field(default_factory=list)
    decision_explanations: List[Any] = Field(default_factory=list)
    critique_result: Optional[Any] = None
    critique_iteration: int = 0
    trace_events: List[AgentTraceEvent] = Field(default_factory=list)
    error: Optional[str] = None
    is_complete: bool = False
