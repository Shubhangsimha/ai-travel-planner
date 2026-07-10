import logging
from app.core.llm import get_llm
from app.agents.json_utils import parse_llm_json

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are a travel planning advisor explaining your reasoning.
Return ONLY a valid JSON object — no markdown, no explanation.

JSON schema:
{
  "explanations": [
    {
      "title": "short decision title",
      "reasoning": "1-2 sentence explanation of why this decision was made",
      "alternatives_considered": ["alternative 1", "alternative 2"],
      "constraint_satisfied": "which user constraint this satisfies"
    }
  ]
}

Explain exactly 5 decisions. Focus on the most impactful choices:
- Why this hotel/area was chosen
- Why specific attractions match the user's interests
- How the budget was allocated
- Why the day order/structure was chosen
- How a specific user constraint shaped the plan"""

_USER_PROMPT_TEMPLATE = """Explain the 5 most important decisions in this travel plan:

ORIGINAL GOAL: {raw_input}
INTERESTS: {interests}
EXCLUSIONS: {exclusions}
BUDGET USED: INR {total_cost:,.0f} of INR {budget_limit:,.0f}

KEY PLAN HIGHLIGHTS:
{highlights}

Return the JSON explanations object."""


def _extract_highlights(itinerary_days: list[dict], budget_breakdown: dict) -> str:
    lines = []

    if itinerary_days:
        day1 = itinerary_days[0]
        lines.append(f"Day 1 morning: {day1.get('morning', {}).get('activity', '')} at {day1.get('morning', {}).get('location', '')}")

    # Most expensive day
    if itinerary_days:
        costliest = max(itinerary_days, key=lambda d: d.get("daily_total_inr", 0))
        lines.append(f"Most expensive day: Day {costliest.get('day_number')} at INR {costliest.get('daily_total_inr', 0):,}")

    lines.append(f"Flight cost: INR {budget_breakdown.get('flights_inr', 0):,}")
    lines.append(f"Accommodation: INR {budget_breakdown.get('accommodation_inr', 0):,}")
    lines.append(f"Activities + food + transport: INR {budget_breakdown.get('activities_food_transport_inr', 0):,}")

    return "\n".join(lines)


def generate_explanations(
    trip_goal: dict,
    itinerary_days: list[dict],
    budget_breakdown: dict,
) -> list[dict]:
    llm = get_llm()

    highlights = _extract_highlights(itinerary_days, budget_breakdown)

    prompt = _USER_PROMPT_TEMPLATE.format(
        raw_input=trip_goal.get("raw_input", ""),
        interests=", ".join(trip_goal.get("interests", [])),
        exclusions=", ".join(trip_goal.get("exclusions", [])) or "none",
        total_cost=budget_breakdown.get("total_inr", 0),
        budget_limit=trip_goal.get("budget_inr", 0),
        highlights=highlights,
    )

    response = llm.invoke([
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ])

    data = parse_llm_json(response.content, context="Explainer")
    return data.get("explanations", [])
