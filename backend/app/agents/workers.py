"""
Tier-2 Research Workers — stateless, parallel, each calls one real API.
All workers return a WorkerResult dict. Errors are stored, never raised.
"""
import asyncio
import logging
import time
from datetime import datetime

from app.clients.geocoding import city_to_coordinates
from app.clients.weather import get_weather_forecast
from app.clients.opentripmap import get_attractions, get_restaurants
from app.clients.exchangerate import get_exchange_rate
from app.clients.aviationstack import aviationstack_flight_search
from app.clients.flight_estimator import estimate_flight_price
from app.clients.overpass import overpass_hotel_search
from app.clients.hotel_estimator import estimate_hotel_price

logger = logging.getLogger(__name__)


def _result(name: str, success: bool, data: dict, is_test_data: bool = False, error: str = None) -> dict:
    return {
        "worker_name": name,
        "success": success,
        "data": data,
        "is_test_data": is_test_data,
        "error": error,
    }


def _trace_event(name: str, status: str, message: str, start_ms: int = 0, query: str = "") -> dict:
    now = int(time.time() * 1000)
    return {
        "agent": name,
        "status": status,
        "message": message,
        "timestamp_ms": now,
        "duration_ms": now - start_ms if start_ms else None,
        "query_summary": query,
    }


async def weather_worker(trip_goal: dict, coords: dict) -> tuple[dict, dict]:
    name = "WeatherWorker"
    start = int(time.time() * 1000)
    try:
        forecasts = await get_weather_forecast(
            coords["lat"], coords["lon"],
            trip_goal["start_date"], trip_goal["end_date"],
        )
        is_proxy = forecasts and forecasts[0].get("seasonal_proxy")
        label = "seasonal proxy (trip >15 days away)" if is_proxy else "forecast"
        trace = _trace_event(
            name, "completed",
            f"Fetched {len(forecasts)} day {label} for {trip_goal['destination']}",
            start, f"{trip_goal['start_date']} to {trip_goal['end_date']}"
        )
        return _result(name, True, {"forecasts": forecasts, "is_proxy": bool(is_proxy)}), trace
    except Exception as e:
        logger.exception("%s failed", name)
        trace = _trace_event(name, "failed", str(e), start)
        return _result(name, False, {}, error=str(e)), trace


async def attractions_worker(trip_goal: dict, coords: dict) -> tuple[dict, dict]:
    name = "AttractionsWorker"
    start = int(time.time() * 1000)
    try:
        attractions = await get_attractions(
            coords["lat"], coords["lon"],
            radius=5000,
            interests=trip_goal.get("interests", []),
        )
        trace = _trace_event(
            name, "completed",
            f"Found {len(attractions)} attractions matching interests",
            start, str(trip_goal.get("interests", []))
        )
        return _result(name, True, {"attractions": attractions}), trace
    except Exception as e:
        logger.exception("%s failed", name)
        trace = _trace_event(name, "failed", str(e), start)
        return _result(name, False, {}, error=str(e)), trace


async def restaurant_worker(trip_goal: dict, coords: dict) -> tuple[dict, dict]:
    name = "RestaurantWorker"
    start = int(time.time() * 1000)
    try:
        restaurants = await get_restaurants(coords["lat"], coords["lon"])
        trace = _trace_event(
            name, "completed",
            f"Found {len(restaurants)} restaurants near {trip_goal['destination']}",
            start, f"lat={coords['lat']:.4f}, lon={coords['lon']:.4f}"
        )
        return _result(name, True, {"restaurants": restaurants}), trace
    except Exception as e:
        logger.exception("%s failed", name)
        trace = _trace_event(name, "failed", str(e), start)
        return _result(name, False, {}, error=str(e)), trace


async def currency_worker(trip_goal: dict) -> tuple[dict, dict]:
    name = "CurrencyWorker"
    start = int(time.time() * 1000)
    try:
        dest_currency = trip_goal.get("currency", "JPY")
        rate_data = await get_exchange_rate("INR", dest_currency)
        budget_inr = trip_goal.get("budget_inr", 0)
        converted = round(budget_inr * rate_data["rate"])
        trace = _trace_event(
            name, "completed",
            f"INR {budget_inr:,.0f} = {dest_currency} {converted:,} (rate: {rate_data['rate']})",
            start, "INR to destination currency"
        )
        return _result(name, True, {
            "rate": rate_data["rate"],
            "from": "INR",
            "to": dest_currency,
            "budget_inr": budget_inr,
            "budget_converted": converted,
            "is_live": rate_data.get("is_live", False),
        }), trace
    except Exception as e:
        logger.exception("%s failed", name)
        trace = _trace_event(name, "failed", str(e), start)
        return _result(name, False, {}, error=str(e)), trace


async def flight_worker(trip_goal: dict) -> tuple[dict, dict]:
    name = "FlightWorker"
    start = int(time.time() * 1000)
    try:
        origin_iata = trip_goal.get("origin_iata", "DEL")
        dest_iata = trip_goal.get("destination_iata", "TYO")
        travel_month = _month_from_date(trip_goal.get("start_date", ""))

        routes = await aviationstack_flight_search(origin_iata, dest_iata)
        estimate = estimate_flight_price(
            trip_goal.get("origin_city", "delhi"),
            trip_goal.get("destination", "tokyo"),
            travel_month=travel_month,
            is_domestic=trip_goal.get("is_domestic", False),
        )

        trace = _trace_event(
            name, "completed",
            f"Found {len(routes.get('routes', []))} routes, estimated fare INR {estimate['estimated_price_inr']:,}",
            start, f"{origin_iata} to {dest_iata}"
        )
        return _result(name, True, {
            "routes": routes.get("routes", [])[:3],
            "price_estimate": estimate,
            "is_estimated": True,
            "caveat": "Prices are computed estimates. Real-time fares require a paid booking API.",
        }, is_test_data=True), trace
    except Exception as e:
        logger.exception("%s failed", name)
        trace = _trace_event(name, "failed", str(e), start)
        return _result(name, False, {}, error=str(e)), trace


async def hotel_worker(trip_goal: dict, coords: dict) -> tuple[dict, dict]:
    name = "HotelWorker"
    start = int(time.time() * 1000)
    try:
        hotels_raw = await overpass_hotel_search(coords["lat"], coords["lon"], radius_m=5000)
        duration = max(trip_goal.get("duration_days", 7) - 1, 1)
        hotel_budget = trip_goal.get("budget_inr", 120000) * 0.35
        hotels_priced = estimate_hotel_price(
            trip_goal.get("destination", "tokyo"),
            duration,
            hotel_budget,
            hotels_raw,
        )
        trace = _trace_event(
            name, "completed",
            f"Found {len(hotels_raw)} hotels, priced {len(hotels_priced)} options",
            start, f"radius 5km around {trip_goal['destination']}"
        )
        return _result(name, True, {
            "hotels": hotels_priced,
            "is_estimated": True,
            "caveat": "Prices are tier-based estimates. Real availability requires a booking API.",
        }, is_test_data=True), trace
    except Exception as e:
        logger.exception("%s failed", name)
        trace = _trace_event(name, "failed", str(e), start)
        return _result(name, False, {}, error=str(e)), trace


def _month_from_date(date_str: str) -> int:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").month
    except Exception:
        return 10


async def run_all_workers(trip_goal: dict) -> tuple[dict, list[dict]]:
    """
    Geocode the destination, then dispatch all 6 workers in parallel.
    Returns (worker_results dict keyed by worker name, trace_events list).
    """
    destination = trip_goal.get("destination", "Tokyo")
    coords = await city_to_coordinates(destination)
    if not coords:
        logger.warning("Geocoding failed for '%s' — workers will have no location data", destination)
        # Return a clear error rather than silently using Tokyo coordinates
        error_trace = {
            "agent": "WorkerDispatcher",
            "status": "failed",
            "message": f"Could not locate '{destination}' — try a more specific city name",
            "timestamp_ms": int(time.time() * 1000),
        }
        empty_results = {
            name: {"worker_name": name, "success": False, "data": {}, "is_test_data": False,
                   "error": f"Geocoding failed for '{destination}'"}
            for name in ["WeatherWorker", "AttractionsWorker", "RestaurantWorker",
                         "CurrencyWorker", "FlightWorker", "HotelWorker"]
        }
        return empty_results, [error_trace]

    results = await asyncio.gather(
        weather_worker(trip_goal, coords),
        attractions_worker(trip_goal, coords),
        restaurant_worker(trip_goal, coords),
        currency_worker(trip_goal),
        flight_worker(trip_goal),
        hotel_worker(trip_goal, coords),
    )

    worker_results = {}
    trace_events = []
    for result, trace in results:
        worker_results[result["worker_name"]] = result
        trace_events.append(trace)

    return worker_results, trace_events
