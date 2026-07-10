import logging
import httpx

logger = logging.getLogger(__name__)

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

WMO_DESCRIPTIONS: dict[int, str] = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Icy fog", 51: "Light drizzle", 53: "Moderate drizzle",
    55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
    80: "Slight showers", 81: "Moderate showers", 82: "Violent showers",
    95: "Thunderstorm", 96: "Thunderstorm with hail",
}


async def get_weather_forecast(
    lat: float,
    lon: float,
    start_date: str,
    end_date: str,
) -> list[dict]:
    """
    Fetch daily weather from Open-Meteo.
    Uses forecast endpoint for future dates, archive endpoint for past dates.
    Completely free — no API key required.
    """
    from datetime import date as _date, timedelta as _td
    today = _date.today()
    today_str = today.isoformat()
    max_forecast = (today + _td(days=15)).isoformat()

    beyond_window = False
    if start_date < today_str:
        url = ARCHIVE_URL
    else:
        url = FORECAST_URL
        if start_date > max_forecast:
            # Trip is beyond 15-day forecast window — fetch current conditions
            # as a seasonal proxy. Caller should note this in the summary.
            beyond_window = True
            start_date = today_str
            end_date = max_forecast

    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": [
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "precipitation_sum",
            "windspeed_10m_max",
        ],
        "timezone": "auto",
        "start_date": start_date,
        "end_date": end_date,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            daily = data.get("daily", {})

            dates = daily.get("time", [])
            forecasts = []
            for i, date in enumerate(dates):
                code = daily.get("weather_code", [0])[i] if i < len(daily.get("weather_code", [])) else 0
                forecasts.append({
                    "date": date,
                    "description": WMO_DESCRIPTIONS.get(code, "Unknown"),
                    "temp_max_c": daily.get("temperature_2m_max", [None])[i],
                    "temp_min_c": daily.get("temperature_2m_min", [None])[i],
                    "precipitation_mm": daily.get("precipitation_sum", [0])[i],
                    "wind_kmh": daily.get("windspeed_10m_max", [0])[i],
                })

            if beyond_window:
                # Tag every forecast entry so downstream can warn the user
                for f in forecasts:
                    f["seasonal_proxy"] = True

            return forecasts

        except Exception as e:
            logger.error("Open-Meteo error: %s", e)
            return []
