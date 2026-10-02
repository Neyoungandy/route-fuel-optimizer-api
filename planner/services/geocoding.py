from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import asdict
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.core.cache import cache

from planner.exceptions import LocationNotFoundError, UpstreamServiceError
from planner.models import GeoPoint

logger = logging.getLogger(__name__)

_NOMINATIM_MIN_INTERVAL = 1.05
_last_nominatim_call = 0.0


def _cache_key(query: str) -> str:
    digest = hashlib.sha256(query.casefold().strip().encode("utf-8")).hexdigest()
    return f"geocode:v2:{digest}"


def geocode_us_place(query: str) -> GeoPoint:
    cached = cache.get(_cache_key(query))
    if cached:
        return GeoPoint(**cached)

    params = {
        "q": query,
        "format": "jsonv2",
        "limit": 1,
        "countrycodes": "us",
        "addressdetails": 1,
    }
    payload = _nominatim_get(params)
    if not payload:
        params["q"] = f"{query}, USA"
        payload = _nominatim_get(params)
    if not payload:
        raise LocationNotFoundError(f"Could not find a US location for '{query}'.")

    hit = payload[0]
    address = hit.get("address") or {}
    country_code = (address.get("country_code") or "us").lower()
    if country_code != "us":
        raise LocationNotFoundError(f"'{query}' resolved outside the United States.")

    point = GeoPoint(
        latitude=float(hit["lat"]),
        longitude=float(hit["lon"]),
        label=query,
        display_name=hit.get("display_name") or query,
    )
    cache.set(_cache_key(query), asdict(point), timeout=None)
    return point


def _nominatim_get(params: dict) -> list:
    global _last_nominatim_call
    wait = _NOMINATIM_MIN_INTERVAL - (time.monotonic() - _last_nominatim_call)
    if wait > 0:
        time.sleep(wait)

    headers = {"User-Agent": settings.NOMINATIM_USER_AGENT, "Accept": "application/json"}
    try:
        response = requests.get(
            settings.NOMINATIM_URL,
            params=params,
            headers=headers,
            timeout=settings.HTTP_TIMEOUT_SECONDS,
        )
        _last_nominatim_call = time.monotonic()
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        logger.exception("Nominatim request failed")
        raise UpstreamServiceError("Geocoding service is unavailable.") from exc

    return data if isinstance(data, list) else []


def osm_route_url(start: GeoPoint, finish: GeoPoint) -> str:
    query = urlencode(
        {
            "engine": "fossgis_osrm_car",
            "route": f"{start.latitude},{start.longitude};{finish.latitude},{finish.longitude}",
        }
    )
    return f"https://www.openstreetmap.org/directions?{query}"
