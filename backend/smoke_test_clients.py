"""
Run with: python smoke_test_clients.py
Tests all API clients against real endpoints.
"""
import asyncio
import json
import os
import sys

# Force UTF-8 output on Windows terminals
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app.clients.geocoding import city_to_coordinates
from app.clients.weather import get_weather_forecast
from app.clients.opentripmap import get_attractions, get_restaurants
from app.clients.exchangerate import get_exchange_rate
from app.clients.aviationstack import aviationstack_flight_search
from app.clients.flight_estimator import estimate_flight_price
from app.clients.overpass import overpass_hotel_search
from app.clients.hotel_estimator import estimate_hotel_price


def pretty(label: str, data) -> None:
    print(f"\n{'='*50}")
    print(f"  {label}")
    print('='*50)
    print(json.dumps(data, indent=2, default=str)[:800])


async def main():
    print("\nTripPilot AI — API Client Smoke Tests")
    print("Target city: Tokyo, Japan\n")

    # 1. Geocoding
    coords = await city_to_coordinates("Tokyo, Japan")
    pretty("Nominatim — Tokyo coordinates", coords)

    if not coords:
        print("FATAL: Geocoding failed — cannot run remaining tests")
        return

    lat, lon = coords["lat"], coords["lon"]

    # 2. Weather — use near-future dates within forecast window (~16 days ahead)
    from datetime import date, timedelta
    start = (date.today() + timedelta(days=2)).isoformat()
    end = (date.today() + timedelta(days=9)).isoformat()
    weather = await get_weather_forecast(lat, lon, start, end)
    pretty("Open-Meteo — Weather forecast (first 2 days)", weather[:2])

    # 3. Attractions
    attractions = await get_attractions(lat, lon, radius=3000, interests=["anime", "photography"])
    pretty("OpenTripMap — Attractions (first 3)", attractions[:3])

    # 4. Restaurants
    restaurants = await get_restaurants(lat, lon)
    pretty("OpenTripMap — Restaurants (first 3)", restaurants[:3])

    # 5. Exchange rate
    rate = await get_exchange_rate("INR", "JPY")
    pretty("ExchangeRate-API — INR to JPY", rate)

    # 6. Aviationstack flights
    flights = await aviationstack_flight_search("DEL", "NRT")
    pretty("Aviationstack - DEL to NRT routes (first 2)", {**flights, "routes": flights["routes"][:2]})

    # 7. Flight price estimate
    estimate = estimate_flight_price("delhi", "tokyo", travel_month=10)
    pretty("Flight Estimator — DEL→TYO October", estimate)

    # 8. Overpass hotels
    hotels_raw = await overpass_hotel_search(lat, lon, radius_m=3000, limit=10)
    pretty("Overpass API — Hotels near Tokyo (first 3)", hotels_raw[:3])

    # 9. Hotel price estimates
    if hotels_raw:
        hotels_priced = estimate_hotel_price("tokyo", 8, 120000, hotels_raw)
        pretty("Hotel Estimator — Top 3 with prices", hotels_priced[:3])

    print("\nSmoke tests complete.")


if __name__ == "__main__":
    asyncio.run(main())
