import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://api.opentripmap.com/0.1/en/places"

# Interest → OpenTripMap kinds mapping
INTEREST_KINDS: dict[str, str] = {
    "anime": "interesting_places",
    "photography": "historic,architecture,natural",
    "cafe": "interesting_places",
    "food": "interesting_places",
    "temple": "religion",
    "nature": "natural",
    "shopping": "interesting_places",
    "art": "art_galleries",
    "default": "interesting_places",
}


async def _get_places(
    lat: float,
    lon: float,
    radius: int,
    kinds: str,
    limit: int = 10,
) -> list[dict]:
    if not settings.OPENTRIPMAP_API_KEY:
        logger.warning("OPENTRIPMAP_API_KEY not set")
        return []

    params = {
        "apikey": settings.OPENTRIPMAP_API_KEY,
        "radius": radius,
        "lon": lon,
        "lat": lat,
        "kinds": kinds,
        "limit": limit,
        "format": "json",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            response = await client.get(f"{BASE_URL}/radius", params=params)
            response.raise_for_status()
            places = response.json()

            result = []
            for place in places:
                # API returns flat objects with point.lat/lon (not GeoJSON)
                point = place.get("point", {})
                result.append({
                    "name": place.get("name", ""),
                    "kinds": place.get("kinds", ""),
                    "dist_m": place.get("dist", 0),
                    "xid": place.get("xid", ""),
                    "lat": point.get("lat", lat),
                    "lon": point.get("lon", lon),
                    "rate": place.get("rate", 0),
                    "wikidata": place.get("wikidata", ""),
                })

            return [p for p in result if p["name"]]

        except Exception as e:
            logger.error("OpenTripMap error: %s", e)
            return []


async def get_attractions(
    lat: float,
    lon: float,
    radius: int = 5000,
    interests: list[str] | None = None,
) -> list[dict]:
    if interests:
        kinds_parts = []
        for interest in interests:
            kinds_parts.append(INTEREST_KINDS.get(interest.lower(), INTEREST_KINDS["default"]))
        kinds = ",".join(set(",".join(kinds_parts).split(",")))
    else:
        kinds = INTEREST_KINDS["default"]

    return await _get_places(lat, lon, radius, kinds, limit=10)


async def get_restaurants(
    lat: float,
    lon: float,
    radius: int = 3000,
) -> list[dict]:
    return await _get_places(lat, lon, radius, "foods,restaurants,cafes", limit=10)
