export interface TraceEvent {
  agent: string;
  status: "started" | "running" | "completed" | "failed";
  message: string;
  timestamp_ms: number;
  duration_ms?: number;
  query_summary?: string;
}

export interface TimeSlot {
  time: string;
  activity: string;
  location: string;
  estimated_cost_inr: number;
  transport_to_next?: string;
  notes?: string;
}

export interface ItineraryDay {
  day_number: number;
  date: string;
  weather_summary: string;
  morning: TimeSlot | null;
  afternoon: TimeSlot | null;
  evening: TimeSlot | null;
  daily_total_inr: number;
}

export interface BudgetBreakdown {
  flights_inr: number;
  accommodation_inr: number;
  activities_food_transport_inr: number;
  total_inr: number;
  budget_limit_inr: number;
  surplus_deficit_inr: number;
  daily_totals: number[];
}

export interface ConstraintCheck {
  constraint: string;
  status: "passed" | "failed" | "warning";
  detail: string;
}

export interface DecisionExplanation {
  title: string;
  reasoning: string;
  alternatives_considered: string[];
  constraint_satisfied: string;
}

export interface WorkerSummary {
  worker_name: string;
  success: boolean;
  is_test_data: boolean;
  error: string | null;
  summary: string;
}

export interface TripGoal {
  destination: string;
  origin_city: string;
  duration_days: number;
  budget_inr: number;
  start_date: string;
  end_date: string;
  interests: string[];
  exclusions: string[];
  transport_preference: string;
  currency: string;
}

export interface PlanResult {
  session_id: string;
  trip_goal: TripGoal | null;
  worker_results: Record<string, WorkerSummary>;
  itinerary_days: ItineraryDay[];
  budget_breakdown: BudgetBreakdown | null;
  constraint_checks: ConstraintCheck[];
  decision_explanations: DecisionExplanation[];
}

export type SSEMessage =
  | { type: "trace" } & TraceEvent
  | { type: "complete" } & PlanResult
  | { type: "error"; message: string };
