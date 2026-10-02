from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GeoPoint:
    latitude: float
    longitude: float
    label: str
    display_name: str


@dataclass(frozen=True, slots=True)
class Station:
    opis_id: int
    name: str
    address: str
    city: str
    state: str
    retail_price: float
    latitude: float
    longitude: float


@dataclass(frozen=True, slots=True)
class RoutePoint:
    latitude: float
    longitude: float
    miles_from_start: float


@dataclass(frozen=True, slots=True)
class DrivingRoute:
    distance_miles: float
    duration_seconds: float
    geometry: list[list[float]]
    samples: list[RoutePoint]


@dataclass(frozen=True, slots=True)
class CandidateStop:
    station: Station
    miles_from_start: float
    offset_miles: float


@dataclass(frozen=True, slots=True)
class FuelPurchase:
    station: Station
    miles_from_start: float
    gallons: float
    cost_usd: float


@dataclass(frozen=True, slots=True)
class FuelPlan:
    start: GeoPoint
    finish: GeoPoint
    route: DrivingRoute
    stops: list[FuelPurchase]
    gallons_consumed: float
    gallons_purchased: float
    total_fuel_cost_usd: float
