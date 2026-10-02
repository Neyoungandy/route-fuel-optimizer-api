from __future__ import annotations

from planner.exceptions import InfeasibleFuelPlanError
from planner.models import CandidateStop, FuelPurchase


def plan_fuel_stops(
    candidates: list[CandidateStop],
    total_miles: float,
    range_miles: float,
    mpg: float,
) -> list[FuelPurchase]:
    """
    Minimum-cost refueling on a line, given a full tank at departure.

    From the current position, the vehicle can reach any station within the
    remaining range. It always buys at the cheapest reachable station (farthest
    on a tie). If a cheaper station exists within a full tank of that stop, it
    buys only enough to get there; otherwise it fills the tank.
    """
    if total_miles <= range_miles:
        return []

    stations = sorted(candidates, key=lambda c: c.miles_from_start)
    tank_gallons = range_miles / mpg
    fuel_gallons = tank_gallons
    position = 0.0
    purchases: list[FuelPurchase] = []

    while position + fuel_gallons * mpg < total_miles - 1e-6:
        reach = position + fuel_gallons * mpg
        window = [c for c in stations if position + 0.05 < c.miles_from_start <= reach + 1e-6]
        if not window:
            raise InfeasibleFuelPlanError(
                "No priced truck stop lies within the remaining 500-mile range on this route."
            )

        stop = min(window, key=lambda c: (c.station.retail_price, -c.miles_from_start))
        travel_miles = stop.miles_from_start - position
        fuel_gallons -= travel_miles / mpg
        position = stop.miles_from_start

        remaining_trip = total_miles - position
        ahead = [
            c
            for c in stations
            if position + 0.05 < c.miles_from_start <= position + range_miles + 1e-6
        ]
        cheaper = [c for c in ahead if c.station.retail_price < stop.station.retail_price - 1e-9]

        if remaining_trip <= fuel_gallons * mpg + 1e-6:
            buy = 0.0
        elif cheaper:
            need = (cheaper[0].miles_from_start - position) / mpg
            buy = max(0.0, min(tank_gallons - fuel_gallons, need - fuel_gallons))
            if remaining_trip <= range_miles and (
                not cheaper or cheaper[0].miles_from_start > total_miles
            ):
                buy = max(buy, remaining_trip / mpg - fuel_gallons)
        elif remaining_trip <= range_miles:
            buy = max(0.0, remaining_trip / mpg - fuel_gallons)
        else:
            buy = tank_gallons - fuel_gallons

        buy = max(0.0, min(buy, tank_gallons - fuel_gallons))
        if buy < 1e-6 and position + fuel_gallons * mpg < total_miles - 1e-6:
            buy = tank_gallons - fuel_gallons

        if buy > 1e-6:
            fuel_gallons += buy
            purchases.append(
                FuelPurchase(
                    station=stop.station,
                    miles_from_start=stop.miles_from_start,
                    gallons=buy,
                    cost_usd=buy * stop.station.retail_price,
                )
            )

        if buy < 1e-6:
            raise InfeasibleFuelPlanError(
                "Could not assemble a fuel plan without exceeding vehicle range."
            )

    return _merge_repeat_stops(purchases)


def _merge_repeat_stops(purchases: list[FuelPurchase]) -> list[FuelPurchase]:
    merged: list[FuelPurchase] = []
    for purchase in purchases:
        if merged and merged[-1].station.opis_id == purchase.station.opis_id:
            gallons = merged[-1].gallons + purchase.gallons
            merged[-1] = FuelPurchase(
                station=purchase.station,
                miles_from_start=purchase.miles_from_start,
                gallons=gallons,
                cost_usd=gallons * purchase.station.retail_price,
            )
        else:
            merged.append(purchase)
    return merged
