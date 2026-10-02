from __future__ import annotations

import math

EARTH_RADIUS_MILES = 3958.7613


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    rlat1, rlon1, rlat2, rlon2 = map(math.radians, (lat1, lon1, lat2, lon2))
    dlat = rlat2 - rlat1
    dlon = rlon2 - rlon1
    a = math.sin(dlat / 2) ** 2 + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_MILES * math.asin(math.sqrt(a))


def planar_miles(lat: float, lon: float) -> tuple[float, float]:
    x = lon * 69.172 * math.cos(math.radians(lat))
    y = lat * 69.172
    return x, y


def polyline_samples(
    lon_lat_coords: list[list[float]],
    step_miles: float = 3.0,
) -> tuple[float, list[tuple[float, float, float]]]:
    if len(lon_lat_coords) < 2:
        raise ValueError("Route geometry is too short.")

    samples: list[tuple[float, float, float]] = []
    total = 0.0
    last_sample_at = 0.0
    lon0, lat0 = lon_lat_coords[0]
    samples.append((lat0, lon0, 0.0))

    for lon, lat in lon_lat_coords[1:]:
        prev_lon, prev_lat = lon0, lat0
        seg = haversine_miles(prev_lat, prev_lon, lat, lon)
        total += seg
        if total - last_sample_at >= step_miles:
            samples.append((lat, lon, total))
            last_sample_at = total
        lon0, lat0 = lon, lat

    last_lon, last_lat = lon_lat_coords[-1]
    if samples[-1][2] < total:
        samples.append((last_lat, last_lon, total))
    return total, samples


def stride_geometry(lon_lat_coords: list[list[float]], max_points: int = 400) -> list[list[float]]:
    n = len(lon_lat_coords)
    if n <= max_points:
        return lon_lat_coords
    step = math.ceil(n / max_points)
    trimmed = lon_lat_coords[::step]
    if trimmed[-1] != lon_lat_coords[-1]:
        trimmed.append(lon_lat_coords[-1])
    return trimmed
