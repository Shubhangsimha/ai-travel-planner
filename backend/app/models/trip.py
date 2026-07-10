from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class TransportPreference(str, Enum):
    public = "public"
    private = "private"
    mixed = "mixed"


class TripGoal(BaseModel):
    destination: str
    origin_city: str = "Delhi"
    duration_days: int
    budget_inr: float
    start_date: str
    end_date: str
    interests: List[str] = Field(default_factory=list)
    exclusions: List[str] = Field(default_factory=list)
    transport_preference: TransportPreference = TransportPreference.public
    raw_input: str = ""


class TimeSlot(BaseModel):
    time: str
    activity: str
    location: str
    estimated_cost_inr: float
    transport_to_next: Optional[str] = None
    notes: Optional[str] = None


class ItineraryDay(BaseModel):
    day_number: int
    date: str
    weather_summary: str = ""
    morning: TimeSlot
    afternoon: TimeSlot
    evening: TimeSlot
    daily_total_inr: float


class BudgetBreakdown(BaseModel):
    flights_inr: float = 0
    accommodation_inr: float = 0
    food_inr: float = 0
    transport_inr: float = 0
    activities_inr: float = 0
    miscellaneous_inr: float = 0
    total_inr: float = 0
    budget_limit_inr: float = 0
    surplus_deficit_inr: float = 0


class ConstraintStatus(str, Enum):
    passed = "passed"
    failed = "failed"
    warning = "warning"


class ConstraintCheck(BaseModel):
    constraint: str
    status: ConstraintStatus
    detail: str


class WorkerResult(BaseModel):
    worker_name: str
    success: bool
    data: dict = Field(default_factory=dict)
    error: Optional[str] = None
    is_test_data: bool = False
