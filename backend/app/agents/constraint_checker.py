"""
Pure Python constraint checker — no LLM involved.
Verifies the final itinerary satisfies all user constraints.
"""

MUSEUM_KEYWORDS = {"museum", "musee", "gallery", "exhibit", "exhibition", "national museum", "art museum", "history museum"}
# Map user exclusion terms to sets of activity keywords to check
EXCLUSION_KEYWORD_MAP: dict[str, set[str]] = {
    "museum":    {"museum", "musee", "exhibit", "exhibition"},
    "gallery":   {"gallery", "galleries", "art gallery", "exhibit"},
    "crowded":   {"tourist", "popular", "busy", "crowded", "peak"},
    "wine":      {"winery", "vineyard", "wine tasting", "wine tour"},
    "alcohol":   {"bar", "pub", "brewery", "winery", "cocktail"},
    "beach":     {"beach", "seaside", "shore", "coastal"},
    "hiking":    {"hiking", "trek", "trail", "summit"},
    "nightlife": {"nightclub", "club", "disco", "bar", "pub"},
}
PRIVATE_TRANSPORT_KEYWORDS = {"taxi", "cab", "uber", "ola", "private car", "rental car", "auto rickshaw"}
PUBLIC_TRANSPORT_KEYWORDS = {"subway", "metro", "bus", "train", "walk", "bicycle", "tram", "monorail", "ferry"}


def check_constraints(
    trip_goal: dict,
    itinerary_days: list[dict],
    budget_breakdown: dict,
    worker_results: dict,
) -> list[dict]:
    checks = []

    # 1. Budget
    total = budget_breakdown.get("total_inr", 0)
    limit = trip_goal.get("budget_inr", 0)
    surplus = limit - total
    checks.append({
        "constraint": "Budget",
        "status": "passed" if surplus >= 0 else "failed",
        "detail": (
            f"INR {total:,.0f} used of INR {limit:,.0f} — "
            f"{'surplus' if surplus >= 0 else 'overrun'} INR {abs(surplus):,.0f}"
        ),
    })

    # 2. Exclusions
    exclusions = [e.lower() for e in trip_goal.get("exclusions", [])]
    violations = []
    for day in itinerary_days:
        for slot in ["morning", "afternoon", "evening"]:
            slot_data = day.get(slot) or {}
            activity = slot_data.get("activity", "").lower()
            location = slot_data.get("location", "").lower()
            text = activity + " " + location
            for excl in exclusions:
                # Direct substring match
                if excl in text:
                    violations.append(f"Day {day.get('day_number')} {slot}: {activity[:50]}")
                    continue
                # Keyword-set match for known categories
                kw_set = EXCLUSION_KEYWORD_MAP.get(excl, set())
                if any(kw in text for kw in kw_set):
                    violations.append(f"Day {day.get('day_number')} {slot}: {activity[:50]}")
    checks.append({
        "constraint": "Exclusions",
        "status": "passed" if not violations else "failed",
        "detail": (
            f"No excluded activities found" if not violations
            else f"Violations: {'; '.join(violations[:3])}"
        ),
    })

    # 3. Transport preference
    pref = trip_goal.get("transport_preference", "public")
    if pref == "public":
        transport_violations = []
        for day in itinerary_days:
            for slot in ["morning", "afternoon", "evening"]:
                transport = (day.get(slot) or {}).get("transport_to_next", "").lower()
                if any(kw in transport for kw in PRIVATE_TRANSPORT_KEYWORDS):
                    transport_violations.append(f"Day {day.get('day_number')} {slot}: {transport}")
        checks.append({
            "constraint": "Public Transport",
            "status": "passed" if not transport_violations else "warning",
            "detail": (
                "All transport is public/walk" if not transport_violations
                else f"Possible private transport: {'; '.join(transport_violations[:2])}"
            ),
        })

    # 4. Interests coverage
    interests = [i.lower() for i in trip_goal.get("interests", [])]
    if interests:
        all_text = " ".join(
            (day.get(slot) or {}).get("activity", "").lower()
            + " " + (day.get(slot) or {}).get("location", "").lower()
            for day in itinerary_days
            for slot in ["morning", "afternoon", "evening"]
        )
        covered = [i for i in interests if i in all_text]
        checks.append({
            "constraint": "Interests Coverage",
            "status": "passed" if len(covered) >= len(interests) * 0.6 else "warning",
            "detail": f"Covered: {', '.join(covered) or 'none'} of {', '.join(interests)}",
        })

    # 5. Weather
    weather_data = worker_results.get("WeatherWorker", {}).get("data", {})
    forecasts = weather_data.get("forecasts", [])
    is_proxy = weather_data.get("is_proxy") or (forecasts and forecasts[0].get("seasonal_proxy"))

    if is_proxy:
        checks.append({
            "constraint": "Weather",
            "status": "warning",
            "detail": "Forecast unavailable for trip dates (>15 days away) — check weather closer to your trip",
        })
    else:
        rain_days = [f["date"] for f in forecasts if f.get("precipitation_mm", 0) > 5]
        checks.append({
            "constraint": "Weather",
            "status": "warning" if rain_days else "passed",
            "detail": (
                f"Rain expected on: {', '.join(rain_days)}" if rain_days
                else "No significant rain expected during trip"
            ),
        })

    # 6. Duration vs days planned
    planned = len(itinerary_days)
    expected = trip_goal.get("duration_days", 0)
    checks.append({
        "constraint": "Itinerary Completeness",
        "status": "passed" if planned == expected else "warning",
        "detail": f"{planned} days planned, {expected} days requested",
    })

    return checks
