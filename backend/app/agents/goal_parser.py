import logging
from datetime import date, timedelta

from app.core.llm import get_llm
from app.agents.json_utils import parse_llm_json

logger = logging.getLogger(__name__)

DESTINATION_CURRENCY = {
    # Japan
    "japan": "JPY", "tokyo": "JPY", "osaka": "JPY", "kyoto": "JPY",
    # SE Asia
    "thailand": "THB", "bangkok": "THB",
    "vietnam": "VND", "hanoi": "VND", "ho chi minh": "VND", "hoi an": "VND",
    "indonesia": "IDR", "bali": "IDR", "jakarta": "IDR",
    "malaysia": "MYR", "kuala lumpur": "MYR",
    "cambodia": "USD", "siem reap": "USD",
    "philippines": "PHP", "manila": "PHP", "cebu": "PHP",
    # City-states / Gulf
    "singapore": "SGD",
    "dubai": "AED", "uae": "AED", "abu dhabi": "AED",
    # Europe
    "uk": "GBP", "london": "GBP",
    "france": "EUR", "paris": "EUR", "amsterdam": "EUR", "berlin": "EUR",
    "spain": "EUR", "barcelona": "EUR", "madrid": "EUR", "rome": "EUR",
    "italy": "EUR", "greece": "EUR", "athens": "EUR", "santorini": "EUR",
    "switzerland": "CHF", "zurich": "CHF",
    # Americas
    "usa": "USD", "new york": "USD", "los angeles": "USD", "san francisco": "USD",
    # South Asia / Sri Lanka
    "sri lanka": "LKR", "colombo": "LKR",
    "nepal": "NPR", "kathmandu": "NPR",
    # India — always INR
    "india": "INR",
    "goa": "INR", "mumbai": "INR", "delhi": "INR", "bangalore": "INR",
    "bengaluru": "INR", "chennai": "INR", "kolkata": "INR", "hyderabad": "INR",
    "jaipur": "INR", "udaipur": "INR", "ahmedabad": "INR", "pune": "INR",
    "kochi": "INR", "cochin": "INR", "kerala": "INR", "varanasi": "INR",
    "agra": "INR", "rishikesh": "INR", "shimla": "INR", "manali": "INR",
    "darjeeling": "INR", "amritsar": "INR", "mysore": "INR", "mysuru": "INR",
    "srinagar": "INR", "leh": "INR", "ladakh": "INR",
}

DESTINATION_IATA = {
    # Japan
    "tokyo": "TYO", "japan": "TYO", "osaka": "KIX", "kyoto": "KIX",
    # SE Asia
    "bangkok": "BKK",
    "vietnam": "HAN", "hanoi": "HAN", "ho chi minh": "SGN",
    "bali": "DPS", "indonesia": "DPS", "jakarta": "CGK",
    "malaysia": "KUL", "kuala lumpur": "KUL",
    "cambodia": "REP", "siem reap": "REP",
    "philippines": "MNL", "manila": "MNL",
    # City-states / Gulf
    "singapore": "SIN",
    "dubai": "DXB", "uae": "DXB", "abu dhabi": "AUH",
    # Europe
    "london": "LHR", "uk": "LHR",
    "paris": "CDG", "france": "CDG",
    "amsterdam": "AMS", "berlin": "BER",
    "barcelona": "BCN", "madrid": "MAD",
    "rome": "FCO", "italy": "FCO",
    "greece": "ATH", "athens": "ATH", "santorini": "JTR",
    "zurich": "ZRH",
    # Americas
    "new york": "JFK", "usa": "JFK", "los angeles": "LAX", "san francisco": "SFO",
    # South Asia
    "sri lanka": "CMB", "colombo": "CMB",
    "nepal": "KTM", "kathmandu": "KTM",
    # India
    "goa": "GOI",
    "mumbai": "BOM",
    "delhi": "DEL",
    "bangalore": "BLR", "bengaluru": "BLR",
    "chennai": "MAA",
    "kolkata": "CCU",
    "hyderabad": "HYD",
    "jaipur": "JAI",
    "ahmedabad": "AMD",
    "pune": "PNQ",
    "kochi": "COK", "cochin": "COK", "kerala": "COK",
    "varanasi": "VNS",
    "agra": "AGR",
    "amritsar": "ATQ",
    "srinagar": "SXR",
    "leh": "IXL", "ladakh": "IXL",
}

# IATA codes for Indian airports (used for domestic trip detection)
INDIA_IATA_CODES = {
    "DEL", "BOM", "BLR", "MAA", "CCU", "HYD", "GOI", "JAI", "AMD",
    "PNQ", "COK", "VNS", "AGR", "ATQ", "SXR", "IXL", "GAU", "IXB",
    "NAG", "IDR", "BHO", "VTZ",
}

_SYSTEM_PROMPT = """You are a travel goal extraction engine.
Extract structured travel information from the user's request.
Return ONLY a valid JSON object — no markdown, no explanation, no code fences.

JSON schema:
{
  "destination": "city name (string)",
  "origin_city": "departure city, default Delhi if not mentioned (string)",
  "duration_days": "number of days as integer",
  "budget_inr": "total budget in Indian Rupees as float (convert if given in other units)",
  "start_date": "YYYY-MM-DD format, infer from month if given, use next occurrence",
  "end_date": "YYYY-MM-DD format, start_date + duration_days",
  "interests": ["list of interest keywords from: anime, photography, food, cafe, temple, nature, shopping, art, hiking, beach, nightlife, architecture"],
  "exclusions": ["list of things to avoid e.g. museums, crowded, expensive"],
  "transport_preference": "one of: public, private, mixed"
}

Rules:
- budget_inr must be a number, not a string
- duration_days must be an integer
- interests must be lowercase strings from the allowed list
- If month is mentioned but no year, use the next future occurrence
- If no origin city, use Delhi
- Never include comments or extra fields"""

_USER_PROMPT_TEMPLATE = """Extract travel goal from this request:

{raw_input}

Today's date: {today}
Return only the JSON object."""


def parse_goal(raw_input: str) -> dict:
    llm = get_llm()
    today = date.today().isoformat()

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _USER_PROMPT_TEMPLATE.format(
            raw_input=raw_input, today=today
        )},
    ]

    response = llm.invoke(messages)
    goal = parse_llm_json(response.content, context="GoalParser")

    # Enrich with derived fields
    dest_lower = goal.get("destination", "").lower()
    origin_lower = goal.get("origin_city", "Delhi").lower()

    dest_iata = DESTINATION_IATA.get(dest_lower)
    if not dest_iata:
        # Best-effort: uppercase first 3 chars as IATA placeholder
        dest_iata = dest_lower[:3].upper() if dest_lower else "UNK"

    origin_iata = DESTINATION_IATA.get(origin_lower, "DEL")

    goal["destination_iata"] = dest_iata
    goal["origin_iata"] = origin_iata
    goal["currency"] = DESTINATION_CURRENCY.get(dest_lower, "USD")

    # Domestic trip: both origin and destination are Indian airports
    goal["is_domestic"] = (
        origin_iata in INDIA_IATA_CODES and dest_iata in INDIA_IATA_CODES
    )
    if goal["is_domestic"]:
        goal["currency"] = "INR"

    goal["raw_input"] = raw_input

    # Validate required numeric fields
    goal["budget_inr"] = max(float(goal.get("budget_inr", 120000)), 1.0)
    goal["duration_days"] = max(int(goal.get("duration_days", 7)), 1)

    # Ensure end_date is consistent with duration
    try:
        start = date.fromisoformat(goal["start_date"])
        goal["end_date"] = (start + timedelta(days=goal["duration_days"] - 1)).isoformat()
    except Exception:
        today_d = date.today()
        goal["start_date"] = today_d.isoformat()
        goal["end_date"] = (today_d + timedelta(days=goal["duration_days"] - 1)).isoformat()

    return goal
