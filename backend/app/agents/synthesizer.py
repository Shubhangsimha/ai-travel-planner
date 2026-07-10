import logging
from app.core.llm import get_llm
from app.agents.json_utils import parse_llm_json

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an expert travel planner. Create a detailed day-by-day itinerary.
Return ONLY a valid JSON object — no markdown, no explanation, no code fences.

JSON schema:
{
  "itinerary_days": [
    {
      "day_number": 1,
      "date": "YYYY-MM-DD",
      "weather_summary": "brief weather note from forecast data if available",
      "morning": {
        "time": "09:00",
        "activity": "activity name and brief description",
        "location": "specific place name",
        "estimated_cost_inr": 500,
        "transport_to_next": "walk / subway / bus",
        "notes": "optional tip"
      },
      "afternoon": { "same structure as morning" },
      "evening": { "same structure as morning" },
      "daily_total_inr": 2500
    }
  ]
}

Rules:
- Every activity must be a REAL place matching the destination
- Strictly avoid anything in the exclusions list
- Match interests: recommend anime shops, photography spots, cafes, local restaurants etc.
- Respect transport_preference — if public, only use subway/bus/walk
- daily_total_inr must be the sum of all slot costs — compute it accurately
- Spread activities geographically sensibly across the day
- First day: account for flight arrival (lighter schedule)
- Last day: account for departure (morning only or half day)"""

_USER_PROMPT_TEMPLATE = """Create a {duration_days}-day itinerary for this trip:

GOAL: {raw_input}

DESTINATION: {destination}
DATES: {start_date} to {end_date}
TOTAL BUDGET: INR {budget_inr:,.0f} (= {currency} {budget_converted:,})
INTERESTS: {interests}
EXCLUSIONS: {exclusions}
TRANSPORT: {transport_preference}

FIXED COSTS (already committed, cannot be changed):
- Flight: INR {flight_estimate:,}
- Accommodation: INR {hotel_budget:,}
- Fixed total: INR {fixed_total:,}

REMAINING BUDGET FOR ACTIVITIES/FOOD/TRANSPORT: INR {available_budget:,}
(approx INR {per_day_budget:,} per day across {duration_days} days)

IMPORTANT: All estimated_cost_inr values across all days must sum to no more than INR {available_budget:,}.
Do NOT include flight or hotel costs in any slot's estimated_cost_inr.

WORKER DATA:
- Weather: {weather_summary}
- Attractions found: {attractions_summary}
- Restaurants found: {restaurants_summary}
- Hotels: {hotels_summary}

{critique_context}

Build the full itinerary. Return only the JSON object."""


def _summarise_worker(worker_results: dict, key: str, limit: int = 5) -> str:
    w = worker_results.get(key, {})
    if not w.get("success"):
        return "No data available"
    data = w.get("data", {})

    if key == "WeatherWorker":
        forecasts = data.get("forecasts", [])
        if not forecasts:
            return "No forecast data"
        is_proxy = data.get("is_proxy") or forecasts[0].get("seasonal_proxy")
        prefix = "[SEASONAL PROXY — actual forecast unavailable for trip dates] " if is_proxy else ""
        summary = "; ".join(
            f"{f['date']}: {f['description']} {f.get('temp_max_c', '')}C"
            for f in forecasts
        )
        return prefix + summary

    if key == "AttractionsWorker":
        items = data.get("attractions", [])[:limit]
        return ", ".join(i["name"] for i in items if i.get("name")) or "None found"

    if key == "RestaurantWorker":
        items = data.get("restaurants", [])[:limit]
        return ", ".join(i["name"] for i in items if i.get("name")) or "None found"

    if key == "HotelWorker":
        hotels = data.get("hotels", [])[:3]
        if not hotels:
            return "No hotels found"
        return "; ".join(
            f"{h['name']} ({h.get('tier','mid')} INR {h.get('estimated_nightly_inr',0):,}/night)"
            for h in hotels
        )
    return "OK"


def synthesize_plan(
    trip_goal: dict,
    worker_results: dict,
    objections: list[str] | None = None,
) -> list[dict]:
    llm = get_llm()

    currency_data = worker_results.get("CurrencyWorker", {}).get("data", {})
    flight_data = worker_results.get("FlightWorker", {}).get("data", {})
    hotel_data = worker_results.get("HotelWorker", {}).get("data", {})

    flight_estimate = flight_data.get("price_estimate", {}).get("estimated_price_inr", 0)

    # Hotel budget: use real estimate if available, else 35% of total
    hotels = hotel_data.get("hotels", [])
    hotel_budget = (
        hotels[0].get("estimated_total_inr", 0)
        if hotels
        else round(trip_goal["budget_inr"] * 0.35)
    )

    # Compute what the LLM actually has to spend on activities/food/transport
    fixed_total = flight_estimate + hotel_budget
    available_budget = max(0, round(trip_goal["budget_inr"] - fixed_total))
    duration = max(trip_goal["duration_days"], 1)
    per_day_budget = round(available_budget / duration)

    critique_context = ""
    if objections:
        critique_context = (
            "PREVIOUS PLAN WAS REJECTED. Fix these issues:\n"
            + "\n".join(f"- {o}" for o in objections)
        )

    prompt = _USER_PROMPT_TEMPLATE.format(
        duration_days=trip_goal["duration_days"],
        raw_input=trip_goal["raw_input"],
        destination=trip_goal["destination"],
        start_date=trip_goal["start_date"],
        end_date=trip_goal["end_date"],
        budget_inr=trip_goal["budget_inr"],
        currency=trip_goal.get("currency", "USD"),
        budget_converted=currency_data.get("budget_converted", 0),
        interests=", ".join(trip_goal.get("interests", [])),
        exclusions=", ".join(trip_goal.get("exclusions", [])) or "none",
        transport_preference=trip_goal.get("transport_preference", "public"),
        weather_summary=_summarise_worker(worker_results, "WeatherWorker"),
        attractions_summary=_summarise_worker(worker_results, "AttractionsWorker"),
        restaurants_summary=_summarise_worker(worker_results, "RestaurantWorker"),
        hotels_summary=_summarise_worker(worker_results, "HotelWorker"),
        flight_estimate=flight_estimate,
        hotel_budget=hotel_budget,
        fixed_total=fixed_total,
        available_budget=available_budget,
        per_day_budget=per_day_budget,
        critique_context=critique_context,
    )

    response = llm.invoke([
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ])

    data = parse_llm_json(response.content, context="Synthesizer")
    if isinstance(data, list):
        return data
    return data.get("itinerary_days", [])


def compute_budget_breakdown(
    itinerary_days: list[dict],
    trip_goal: dict,
    worker_results: dict,
) -> dict:
    """All arithmetic done in Python — never delegated to LLM."""
    flight_est = (
        worker_results.get("FlightWorker", {})
        .get("data", {})
        .get("price_estimate", {})
        .get("estimated_price_inr", 0)
    )

    hotels = worker_results.get("HotelWorker", {}).get("data", {}).get("hotels", [])
    # Use real hotel estimate if available, else same 35% fallback used in synthesizer
    hotel_total = (
        hotels[0].get("estimated_total_inr", 0)
        if hotels
        else round(trip_goal["budget_inr"] * 0.35)
    )

    # Recompute daily totals from slot costs in Python — never trust LLM arithmetic
    recomputed_daily = []
    for day in itinerary_days:
        slot_sum = sum(
            (day.get(slot) or {}).get("estimated_cost_inr", 0)
            for slot in ["morning", "afternoon", "evening"]
        )
        day["daily_total_inr"] = slot_sum  # fix in-place so downstream is consistent
        recomputed_daily.append(slot_sum)

    activities_food_transport = sum(recomputed_daily)
    total = flight_est + hotel_total + activities_food_transport
    surplus = trip_goal["budget_inr"] - total

    return {
        "flights_inr": flight_est,
        "accommodation_inr": hotel_total,
        "activities_food_transport_inr": activities_food_transport,
        "total_inr": round(total),
        "budget_limit_inr": trip_goal["budget_inr"],
        "surplus_deficit_inr": round(surplus),
        "daily_totals": recomputed_daily,
    }
