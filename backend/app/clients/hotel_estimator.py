"""
Tier-based hotel price estimator.
Uses real city cost-of-living data — all arithmetic in Python, never LLM.
"""

# Nightly rates in INR by city and tier
CITY_NIGHTLY_RATES_INR: dict[str, dict[str, float]] = {
    "tokyo": {"budget": 3500, "mid": 7000, "luxury": 18000},
    "osaka": {"budget": 3000, "mid": 6000, "luxury": 15000},
    "kyoto": {"budget": 3200, "mid": 6500, "luxury": 16000},
    "bangkok": {"budget": 1800, "mid": 4000, "luxury": 12000},
    "singapore": {"budget": 5000, "mid": 10000, "luxury": 25000},
    "dubai": {"budget": 4500, "mid": 9000, "luxury": 22000},
    "paris": {"budget": 7000, "mid": 14000, "luxury": 35000},
    "london": {"budget": 8000, "mid": 16000, "luxury": 40000},
    "new york": {"budget": 9000, "mid": 18000, "luxury": 45000},
    # default fallback
    "default": {"budget": 3000, "mid": 6000, "luxury": 15000},
}

# Star rating → tier mapping
STARS_TO_TIER: dict[int, str] = {
    1: "budget", 2: "budget", 3: "mid", 4: "luxury", 5: "luxury",
}


def estimate_hotel_price(
    city: str,
    duration_nights: int,
    budget_inr: float,
    hotels: list[dict],
) -> list[dict]:
    """
    Attach price estimates to a list of hotel POIs.
    Selects tier based on available budget per night.
    """
    city_key = city.lower()
    rates = CITY_NIGHTLY_RATES_INR.get(city_key, CITY_NIGHTLY_RATES_INR["default"])

    # Determine affordable tier from budget
    budget_per_night = budget_inr / max(duration_nights, 1)
    if budget_per_night >= rates["luxury"]:
        tier = "luxury"
    elif budget_per_night >= rates["mid"]:
        tier = "mid"
    else:
        tier = "budget"

    result = []
    for hotel in hotels[:5]:  # top 5 options
        star_str = hotel.get("stars")
        if star_str and str(star_str).isdigit():
            hotel_tier = STARS_TO_TIER.get(int(star_str), tier)
        else:
            hotel_tier = tier

        nightly = rates.get(hotel_tier, rates["mid"])
        result.append({
            **hotel,
            "tier": hotel_tier,
            "estimated_nightly_inr": nightly,
            "estimated_total_inr": round(nightly * duration_nights),
            "duration_nights": duration_nights,
            "is_estimated": True,
            "note": "Price is a tier-based estimate. Not a live rate.",
        })

    return result
