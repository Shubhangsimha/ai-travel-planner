import logging
import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://nominatim.openstreetmap.org/search"


async def city_to_coordinates(city_name: str) -> dict | None:
    """
    Convert a city name to lat/lon using Nominatim (OpenStreetMap).
    Completely free — no API key required.
    """
    params = {
        "q": city_name,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
    }
    headers = {"User-Agent": "TripPilotAI/0.1 (travel-planner-demo)"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(BASE_URL, params=params, headers=headers)
            response.raise_for_status()
            results = response.json()

            if not results:
                logger.warning("Nominatim: no results for '%s'", city_name)
                return None

            first = results[0]
            address = first.get("address", {})
            return {
                "city": city_name,
                "display_name": first.get("display_name", ""),
                "lat": float(first["lat"]),
                "lon": float(first["lon"]),
                "country": address.get("country", ""),
                "country_code": address.get("country_code", "").upper(),
            }

        except Exception as e:
            logger.error("Nominatim error for '%s': %s", city_name, e)
            return None
