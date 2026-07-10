import logging
from app.core.llm import get_llm
from app.agents.json_utils import parse_llm_json

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a strict travel plan quality reviewer.
Evaluate the itinerary against the user's original goals.
Return ONLY a valid JSON object — no markdown, no explanation.

JSON schema:
{
  "approved": true or false,
  "objections": ["list of specific issues found, empty if approved"],
  "score": 1-10
}

Check for ALL of the following:
1. Budget: does the total exceed the stated budget?
2. Exclusions: does any activity violate an exclusion (e.g. museums when excluded)?
3. Interests: are the user's interests reflected (anime, photography spots, cafes, local food)?
4. Transport: if public transport preferred, are private taxis/cars used?
5. Schedule: are day 1 and last day lighter (arrival/departure days)?
6. Variety: is every day different, not repetitive?
7. Realism: are the locations real and geographically sensible within the city?

Be strict. Approve only if all checks pass."""

_USER_PROMPT_TEMPLATE = """Review this travel plan:

ORIGINAL GOAL: {raw_input}
TOTAL BUDGET: INR {budget_inr:,.0f}
INTERESTS: {interests}
EXCLUSIONS: {exclusions}
TRANSPORT: {transport_preference}

FIXED COSTS (cannot be changed by replanning):
- Flight: INR {flight_cost:,}
- Accommodation: INR {hotel_cost:,}

CONTROLLABLE COSTS (activities, food, local transport):
- Spent: INR {activities_cost:,}
- Available: INR {available_budget:,}

TOTAL: INR {total_cost:,.0f} | SURPLUS/DEFICIT: INR {surplus_deficit:,.0f}

ITINERARY SUMMARY:
{itinerary_summary}

IMPORTANT: Do NOT reject solely because flights or accommodation exceed the budget —
those are fixed external costs outside the planner's control. Only reject if:
1. Controllable activity costs exceed the available budget (INR {available_budget:,})
2. Exclusions are violated
3. Interests are not reflected
4. Transport preference is violated

Return the JSON review object."""


def _build_itinerary_summary(itinerary_days: list[dict]) -> str:
    lines = []
    for day in itinerary_days:
        morning = day.get("morning", {})
        afternoon = day.get("afternoon", {})
        evening = day.get("evening", {})
        morning = morning or {}
        afternoon = afternoon or {}
        evening = evening or {}
        lines.append(
            f"Day {day.get('day_number')}: "
            f"Morning: {morning.get('activity', '')[:50]} @ {morning.get('location', '')} | "
            f"Afternoon: {afternoon.get('activity', '')[:50]} @ {afternoon.get('location', '')} | "
            f"Evening: {evening.get('activity', '')[:50]} @ {evening.get('location', '')} | "
            f"Cost: INR {day.get('daily_total_inr', 0):,}"
        )
    return "\n".join(lines)


def critique_plan(
    trip_goal: dict,
    itinerary_days: list[dict],
    budget_breakdown: dict,
    iteration: int,
) -> dict:
    llm = get_llm()

    itinerary_summary = _build_itinerary_summary(itinerary_days)
    surplus = budget_breakdown.get("surplus_deficit_inr", 0)
    total = budget_breakdown.get("total_inr", 0)

    flight_cost = budget_breakdown.get("flights_inr", 0)
    hotel_cost = budget_breakdown.get("accommodation_inr", 0)
    activities_cost = budget_breakdown.get("activities_food_transport_inr", 0)
    available_budget = max(0, round(trip_goal["budget_inr"] - flight_cost - hotel_cost))

    prompt = _USER_PROMPT_TEMPLATE.format(
        raw_input=trip_goal.get("raw_input", ""),
        budget_inr=trip_goal["budget_inr"],
        interests=", ".join(trip_goal.get("interests", [])),
        exclusions=", ".join(trip_goal.get("exclusions", [])) or "none",
        transport_preference=trip_goal.get("transport_preference", "public"),
        flight_cost=flight_cost,
        hotel_cost=hotel_cost,
        activities_cost=activities_cost,
        available_budget=available_budget,
        total_cost=total,
        surplus_deficit=surplus,
        itinerary_summary=itinerary_summary,
    )

    response = llm.invoke([
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ])

    result = parse_llm_json(response.content, context="Critic")
    result["iteration"] = iteration
    return result
