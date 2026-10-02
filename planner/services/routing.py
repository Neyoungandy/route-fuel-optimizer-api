from __future__ import annotations

import hashlib
import logging

import requests
from django.conf import settings
from django.core.cache import cache

from planner.exceptions import RouteNotFoundError, UpstreamServiceError
from planner.models import DrivingRoute, GeoPoint, RoutePoint
from planner.services.geometry import polyline_samples, stride_geometry

logger = logging.getLogger(__name__)


def fetch_driving_route(start: GeoPoint, finish: GeoPoint) -> DrivingRoute:
    seed = f"{start.longitude:.4f},{start.latitude:.4f};{finish.longitude:.4f},{finish.latitude:.4f}"
    key = "osrm:v2:" + hashlib.sha256(seed.encode("utf-8")).hexdigest()
    cached = cache.get(key)
    if cached:
        return _route_from_payload(cached)

    url = (
        f"{settings.OSRM_BASE_URL}/route/v1/driving/"
        f"{start.longitude},{start.latitude};{finish.longitude},{finish.latitude}"
    )
    params = {"overview": "full", "geometries": "geojson", "steps": "false"}
    headers = {"User-Agent": settings.NOMINATIM_USER_AGENT, "Accept": "application/json"}

    try:
        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=settings.HTTP_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as exc:
        logger.exception("OSRM request failed")
        raise UpstreamServiceError("Routing service is unavailable.") from exc

    if payload.get("code") != "Ok" or not payload.get("routes"):
        raise RouteNotFoundError("No driving route was found between those locations.")

    cache.set(key, payload, timeout=None)
    return _route_from_payload(payload)


def _route_from_payload(payload: dict) -> DrivingRoute:
    route = payload["routes"][0]
    coords = route["geometry"]["coordinates"]
    meters = float(route["distance"])
    duration = float(route["duration"])
    sampled_total, samples = polyline_samples(coords, step_miles=3.0)
    distance_miles = meters / 1609.344
    if sampled_total > 0:
        distance_miles = sampled_total

    return DrivingRoute(
        distance_miles=distance_miles,
        duration_seconds=duration,
        geometry=stride_geometry(coords),
        samples=[
            RoutePoint(latitude=lat, longitude=lon, miles_from_start=miles)
            for lat, lon, miles in samples
        ],
    )
