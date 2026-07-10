import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "http://api.aviationstack.com/v1"  # free tier is HTTP only


async def aviationstack_flight_search(
    origin_iata: str,
    destination_iata: str,
) -> dict:
    """
    Fetch real flight routes between two airports.
    Returns route info and airline data — prices are estimated separately.
    Falls back to empty result if key is missing or quota exceeded.
    """
    if not settings.AVIATIONSTACK_API_KEY:
        logger.warning("AVIATIONSTACK_API_KEY not set — FlightWorker will use estimation only")
        return {"is_estimated": True, "routes": []}

    params = {
        "access_key": settings.AVIATIONSTACK_API_KEY,
        "dep_iata": origin_iata.upper(),
        "arr_iata": destination_iata.upper(),
        "limit": 10,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(f"{BASE_URL}/flights", params=params)
            response.raise_for_status()
            data = response.json()

            routes = []
            for flight in data.get("data", []):
                dep = flight.get("departure", {})
                arr = flight.get("arrival", {})
                airline = flight.get("airline", {})
                routes.append({
                    "airline": airline.get("name", "Unknown Airline"),
                    "flight_number": flight.get("flight", {}).get("iata", ""),
                    "departure_airport": dep.get("airport", origin_iata),
                    "arrival_airport": arr.get("airport", destination_iata),
                    "departure_time": dep.get("scheduled", ""),
                    "arrival_time": arr.get("scheduled", ""),
                })

            return {"is_estimated": False, "routes": routes}

        except httpx.HTTPStatusError as e:
            logger.error("Aviationstack HTTP error: %s", e)
            return {"is_estimated": True, "routes": [], "error": str(e)}
        except Exception as e:
            logger.error("Aviationstack unexpected error: %s", e)
            return {"is_estimated": True, "routes": [], "error": str(e)}
