from __future__ import annotations

import hashlib

from django.conf import settings
from django.core.cache import cache

from planner.models import FuelPlan
from planner.services.geocoding import geocode_us_place, osm_route_url
from planner.services.optimizer import plan_fuel_stops
from planner.services.routing import fetch_driving_route
from planner.services.stations import get_station_index


def build_fuel_plan(start_query: str, finish_query: str) -> FuelPlan:
    raw = f"{start_query.casefold().strip()}|{finish_query.casefold().strip()}"
    cache_key = "plan:v5:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    start = geocode_us_place(start_query)
    finish = geocode_us_place(finish_query)
    route = fetch_driving_route(start, finish)

    candidates = get_station_index().along_route(
        route,
        corridor_miles=settings.STATION_CORRIDOR_MILES,
    )
    stops = plan_fuel_stops(
        candidates,
        total_miles=route.distance_miles,
        range_miles=settings.VEHICLE_RANGE_MILES,
        mpg=settings.VEHICLE_MPG,
    )
    gallons_consumed = route.distance_miles / settings.VEHICLE_MPG
    gallons_purchased = sum(stop.gallons for stop in stops)
    total_cost = sum(stop.cost_usd for stop in stops)

    plan = FuelPlan(
        start=start,
        finish=finish,
        route=route,
        stops=stops,
        gallons_consumed=gallons_consumed,
        gallons_purchased=gallons_purchased,
        total_fuel_cost_usd=total_cost,
    )
    cache.set(cache_key, plan, timeout=None)
    return plan


def serialize_plan(plan: FuelPlan) -> dict:
    start, finish = plan.start, plan.finish
    return {
        "vehicle": {
            "range_miles": settings.VEHICLE_RANGE_MILES,
            "mpg": settings.VEHICLE_MPG,
            "starts_with_full_tank": True,
        },
        "start": {
            "query": start.label,
            "display_name": start.display_name,
            "latitude": round(start.latitude, 6),
            "longitude": round(start.longitude, 6),
        },
        "finish": {
            "query": finish.label,
            "display_name": finish.display_name,
            "latitude": round(finish.latitude, 6),
            "longitude": round(finish.longitude, 6),
        },
        "route": {
            "distance_miles": round(plan.route.distance_miles, 1),
            "duration_minutes": round(plan.route.duration_seconds / 60.0, 1),
            "map_url": osm_route_url(start, finish),
            "geometry": {
                "type": "LineString",
                "coordinates": plan.route.geometry,
            },
        },
        "fuel": {
            "gallons_consumed": round(plan.gallons_consumed, 2),
            "gallons_purchased": round(plan.gallons_purchased, 2),
            "total_fuel_cost_usd": round(plan.total_fuel_cost_usd, 2),
            "stops": [_serialize_stop(index, stop) for index, stop in enumerate(plan.stops, start=1)],
        },
    }


def _serialize_stop(sequence: int, purchase) -> dict:
    station = purchase.station
    return {
        "sequence": sequence,
        "opis_id": station.opis_id,
        "name": station.name,
        "address": station.address,
        "city": station.city,
        "state": station.state,
        "latitude": round(station.latitude, 6),
        "longitude": round(station.longitude, 6),
        "miles_from_start": round(purchase.miles_from_start, 1),
        "retail_price_usd": round(station.retail_price, 3),
        "gallons": round(purchase.gallons, 2),
        "cost_usd": round(purchase.cost_usd, 2),
    }
