from __future__ import annotations

import csv
import logging
import re
import threading
from functools import lru_cache
from pathlib import Path

import numpy as np
from django.conf import settings
from scipy.spatial import cKDTree

from planner.models import CandidateStop, DrivingRoute, Station
from planner.services.geometry import haversine_miles, planar_miles

logger = logging.getLogger(__name__)

_CITY_NORMALIZER = re.compile(r"[^A-Z0-9]+")
_CANADIAN_REGIONS = {"AB", "BC", "MB", "NB", "NL", "NS", "NT", "NU", "ON", "PE", "QC", "SK", "YT"}
_load_lock = threading.Lock()
_INDEX: "StationIndex | None" = None


def _norm_city(value: str) -> str:
    cleaned = value.upper().replace(".", " ")
    cleaned = cleaned.replace("SAINT ", "ST ").replace("FORT ", "FT ")
    return _CITY_NORMALIZER.sub("", cleaned)


def _load_city_lookup(path: Path) -> dict[tuple[str, str], tuple[float, float]]:
    lookup: dict[tuple[str, str], tuple[float, float]] = {}
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        reader.fieldnames = [name.strip() for name in (reader.fieldnames or [])]
        for row in reader:
            state = (row.get("STATE_CODE") or "").strip().upper()
            city = _norm_city(row.get("CITY") or "")
            if not state or not city:
                continue
            try:
                lat = float(row["LATITUDE"])
                lon = float(row["LONGITUDE"])
            except (KeyError, TypeError, ValueError):
                continue
            lookup[(city, state)] = (lat, lon)
    return lookup


def load_stations(fuel_csv: Path, cities_csv: Path) -> list[Station]:
    cities = _load_city_lookup(cities_csv)
    by_id: dict[int, Station] = {}
    skipped = 0

    with fuel_csv.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        reader.fieldnames = [name.strip() for name in (reader.fieldnames or [])]
        for row in reader:
            try:
                opis_id = int(float(row["OPIS Truckstop ID"]))
                price = float(row["Retail Price"])
            except (KeyError, TypeError, ValueError):
                skipped += 1
                continue
            if price <= 0:
                skipped += 1
                continue

            state = (row.get("State") or "").strip().upper()
            if state in _CANADIAN_REGIONS:
                skipped += 1
                continue
            city_raw = (row.get("City") or "").strip()
            coords = cities.get((_norm_city(city_raw), state))
            if coords is None:
                skipped += 1
                continue

            station = Station(
                opis_id=opis_id,
                name=(row.get("Truckstop Name") or "").strip(),
                address=(row.get("Address") or "").strip(),
                city=city_raw,
                state=state,
                retail_price=price,
                latitude=coords[0],
                longitude=coords[1],
            )
            existing = by_id.get(opis_id)
            if existing is None or station.retail_price < existing.retail_price:
                by_id[opis_id] = station

    stations = list(by_id.values())
    logger.info("Loaded %s fuel stations (%s rows skipped)", len(stations), skipped)
    if len(stations) < 1000:
        raise RuntimeError("Fuel station catalog is too small to plan routes.")
    return stations


class StationIndex:
    def __init__(self, stations: list[Station]):
        self.stations = stations
        xy = np.array([planar_miles(s.latitude, s.longitude) for s in stations], dtype=float)
        self._tree = cKDTree(xy)

    def along_route(self, route: DrivingRoute, corridor_miles: float) -> list[CandidateStop]:
        best: dict[int, tuple[float, float]] = {}
        samples = route.samples
        if not samples:
            return []

        points = np.array(
            [planar_miles(p.latitude, p.longitude) for p in samples],
            dtype=float,
        )
        neighbor_lists = self._tree.query_ball_point(points, r=corridor_miles)

        for sample, neighbor_ids in zip(samples, neighbor_lists):
            for idx in neighbor_ids:
                station = self.stations[idx]
                offset = haversine_miles(
                    sample.latitude,
                    sample.longitude,
                    station.latitude,
                    station.longitude,
                )
                if offset > corridor_miles:
                    continue
                prev = best.get(idx)
                if prev is None or offset < prev[0]:
                    best[idx] = (offset, sample.miles_from_start)

        candidates = [
            CandidateStop(
                station=self.stations[idx],
                miles_from_start=miles,
                offset_miles=offset,
            )
            for idx, (offset, miles) in best.items()
            if 0.5 < miles < route.distance_miles - 0.5
        ]
        candidates.sort(key=lambda item: (item.miles_from_start, item.station.retail_price))
        return _collapse_nearby(candidates)


def _collapse_nearby(candidates: list[CandidateStop], window_miles: float = 25.0) -> list[CandidateStop]:
    kept: list[CandidateStop] = []
    for candidate in candidates:
        if kept and abs(candidate.miles_from_start - kept[-1].miles_from_start) < window_miles:
            if candidate.station.retail_price < kept[-1].station.retail_price:
                kept[-1] = candidate
            continue
        kept.append(candidate)
    return kept


def get_station_index() -> StationIndex:
    global _INDEX
    if _INDEX is not None:
        return _INDEX
    with _load_lock:
        if _INDEX is None:
            stations = load_stations(settings.FUEL_PRICES_CSV, settings.US_CITIES_CSV)
            _INDEX = StationIndex(stations)
    return _INDEX


@lru_cache(maxsize=1)
def station_count() -> int:
    return len(get_station_index().stations)
