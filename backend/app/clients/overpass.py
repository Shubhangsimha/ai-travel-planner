import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


async def overpass_hotel_search(
    lat: float,
    lon: float,
    radius_m: int = 5000,
    limit: int = 15,
) -> list[dict]:
    """
    Query OpenStreetMap via Overpass API for real hotel POIs.
    Returns hotel names, addresses, and star ratings where available.
    Completely free — no API key required.
    """
    query = f"""
    [out:json][timeout:25];
    (
      node["tourism"="hotel"](around:{radius_m},{lat},{lon});
      way["tourism"="hotel"](around:{radius_m},{lat},{lon});
    );
    out body center {limit};
    """

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                settings.OVERPASS_API_URL,
                params={"data": query},
                headers={"User-Agent": "TripPilotAI/0.1 (travel-planner-demo)"},
            )
            response.raise_for_status()
            data = response.json()

            hotels = []
            for element in data.get("elements", []):
                tags = element.get("tags", {})
                name = tags.get("name") or tags.get("name:en")
                if not name:
                    continue

                # Get coordinates — nodes have direct lat/lon, ways have center
                if element["type"] == "node":
                    h_lat, h_lon = element.get("lat"), element.get("lon")
                else:
                    center = element.get("center", {})
                    h_lat, h_lon = center.get("lat"), center.get("lon")

                hotels.append({
                    "name": name,
                    "lat": h_lat,
                    "lon": h_lon,
                    "stars": tags.get("stars"),
                    "address": tags.get("addr:full") or tags.get("addr:street", ""),
                    "website": tags.get("website", ""),
                    "phone": tags.get("phone", ""),
                })

            return hotels

        except httpx.HTTPStatusError as e:
            logger.error("Overpass HTTP error: %s", e)
            return []
        except Exception as e:
            logger.error("Overpass unexpected error: %s", e)
            return []
