"""
Python-computed flight price estimator.
Uses real distance data and seasonal multipliers — no external API.
All arithmetic is done here, never by an LLM.
"""

# Approximate great-circle distances in km
ROUTE_DISTANCES_KM: dict[tuple, float] = {
    # International — India outbound
    ("DEL", "TYO"): 5850, ("DEL", "NRT"): 5850, ("DEL", "HND"): 5870,
    ("BOM", "TYO"): 6740, ("BOM", "NRT"): 6740,
    ("DEL", "KIX"): 5550, ("DEL", "OSA"): 5550,
    ("DEL", "BKK"): 3940, ("BOM", "BKK"): 3800,
    ("DEL", "SIN"): 5600, ("BOM", "SIN"): 5200,
    ("DEL", "DXB"): 2200, ("BOM", "DXB"): 1930,
    ("DEL", "LHR"): 6700, ("BOM", "LHR"): 7190,
    ("DEL", "CDG"): 6600, ("DEL", "JFK"): 11750,
    ("DEL", "DPS"): 5680, ("BOM", "DPS"): 5270,  # Bali
    ("DEL", "KUL"): 4920, ("BOM", "KUL"): 4330,
    ("DEL", "HAN"): 4290, ("DEL", "SGN"): 4680,
    ("DEL", "CMB"): 2110, ("BOM", "CMB"): 1730,  # Sri Lanka
    ("DEL", "KTM"): 930,                           # Nepal
    # Domestic India
    ("DEL", "GOI"): 1900, ("BOM", "GOI"): 590,
    ("DEL", "BOM"): 1160, ("DEL", "BLR"): 2170,
    ("DEL", "MAA"): 2190, ("DEL", "CCU"): 1310,
    ("DEL", "HYD"): 1870, ("DEL", "COK"): 2690,
    ("DEL", "JAI"): 260,  ("DEL", "AMD"): 950,
    ("DEL", "PNQ"): 1410, ("DEL", "SXR"): 880,
    ("DEL", "IXL"): 610,  ("DEL", "VNS"): 810,
    ("BOM", "BLR"): 990,  ("BOM", "MAA"): 1060,
    ("BOM", "HYD"): 710,  ("BOM", "CCU"): 2040,
    ("BOM", "JAI"): 1150, ("BOM", "COK"): 1200,
}

# Base fare per km — domestic is cheaper per km than international
BASE_FARE_INTERNATIONAL_INR = 5.2
BASE_FARE_DOMESTIC_INR = 4.5

# Indian airport codes (for domestic fare rate selection)
INDIA_IATA = {
    "DEL", "BOM", "BLR", "MAA", "CCU", "HYD", "GOI", "JAI", "AMD",
    "PNQ", "COK", "VNS", "AGR", "ATQ", "SXR", "IXL", "GAU", "IXB",
}

# Seasonal multipliers (month → multiplier)
SEASON_MULTIPLIERS: dict[int, float] = {
    1: 1.1, 2: 1.0, 3: 1.05, 4: 1.0, 5: 0.95, 6: 0.9,
    7: 0.95, 8: 1.0, 9: 1.05, 10: 1.2, 11: 1.3, 12: 1.4,
}

# City name → IATA (used when IATA not already resolved)
CITY_TO_IATA: dict[str, str] = {
    "tokyo": "TYO", "japan": "TYO", "osaka": "KIX",
    "delhi": "DEL", "mumbai": "BOM", "bangalore": "BLR", "bengaluru": "BLR",
    "goa": "GOI", "chennai": "MAA", "kolkata": "CCU", "hyderabad": "HYD",
    "jaipur": "JAI", "kochi": "COK", "cochin": "COK", "pune": "PNQ",
    "ahmedabad": "AMD", "srinagar": "SXR", "leh": "IXL", "ladakh": "IXL",
    "varanasi": "VNS",
    "bangkok": "BKK", "singapore": "SIN", "dubai": "DXB",
    "london": "LHR", "paris": "CDG", "new york": "JFK",
    "bali": "DPS", "kuala lumpur": "KUL", "hanoi": "HAN",
    "sri lanka": "CMB", "colombo": "CMB", "nepal": "KTM", "kathmandu": "KTM",
}

DEFAULT_DISTANCE_KM = 5000  # fallback for unknown international routes
DEFAULT_DOMESTIC_DISTANCE_KM = 1500  # fallback for unknown domestic routes


def estimate_flight_price(
    origin: str,
    destination: str,
    travel_month: int = 10,
    passengers: int = 1,
    is_domestic: bool = False,
) -> dict:
    origin_iata = CITY_TO_IATA.get(origin.lower(), origin.upper()[:3])
    dest_iata = CITY_TO_IATA.get(destination.lower(), destination.upper()[:3])

    # No flight needed for same city
    if origin_iata == dest_iata:
        return {
            "origin_iata": origin_iata,
            "destination_iata": dest_iata,
            "distance_km": 0,
            "estimated_price_inr": 0,
            "estimated_price_inr_per_person": 0,
            "travel_month": travel_month,
            "season_multiplier": 1.0,
            "is_estimated": True,
            "is_domestic": True,
            "note": "Origin and destination are the same — no flight cost.",
        }

    both_india = origin_iata in INDIA_IATA and dest_iata in INDIA_IATA
    domestic = is_domestic or both_india

    default_dist = DEFAULT_DOMESTIC_DISTANCE_KM if domestic else DEFAULT_DISTANCE_KM
    distance = (
        ROUTE_DISTANCES_KM.get((origin_iata, dest_iata))
        or ROUTE_DISTANCES_KM.get((dest_iata, origin_iata))
        or default_dist
    )

    base_rate = BASE_FARE_DOMESTIC_INR if domestic else BASE_FARE_INTERNATIONAL_INR
    season = SEASON_MULTIPLIERS.get(travel_month, 1.0)
    base = distance * base_rate * season

    return {
        "origin_iata": origin_iata,
        "destination_iata": dest_iata,
        "distance_km": distance,
        "estimated_price_inr": round(base * passengers),
        "estimated_price_inr_per_person": round(base),
        "travel_month": travel_month,
        "season_multiplier": season,
        "is_estimated": True,
        "is_domestic": domestic,
        "note": "Price is a computed estimate based on distance and season. Not a live fare.",
    }
