from django.test import SimpleTestCase

from planner.exceptions import InfeasibleFuelPlanError
from planner.models import CandidateStop, Station
from planner.services.optimizer import plan_fuel_stops


def _station(opis_id: int, price: float, city: str = "Town") -> Station:
    return Station(
        opis_id=opis_id,
        name=f"Stop {opis_id}",
        address="I-40",
        city=city,
        state="TX",
        retail_price=price,
        latitude=32.0,
        longitude=-96.0,
    )


def _candidate(opis_id: int, miles: float, price: float) -> CandidateStop:
    return CandidateStop(station=_station(opis_id, price), miles_from_start=miles, offset_miles=1.0)


class FuelOptimizerTests(SimpleTestCase):
    def test_short_trip_needs_no_purchase(self):
        stops = plan_fuel_stops([_candidate(1, 100, 3.0)], total_miles=400, range_miles=500, mpg=10)
        self.assertEqual(stops, [])

    def test_buys_only_what_is_needed_at_cheapest_reachable_stop(self):
        candidates = [_candidate(1, 200, 2.50), _candidate(2, 350, 4.00)]
        stops = plan_fuel_stops(candidates, total_miles=600, range_miles=500, mpg=10)
        self.assertEqual(len(stops), 1)
        self.assertEqual(stops[0].station.opis_id, 1)
        self.assertAlmostEqual(stops[0].gallons, 10.0, places=2)

    def test_skips_expensive_station_when_cheaper_is_still_in_range(self):
        candidates = [_candidate(1, 100, 4.00), _candidate(2, 300, 2.00)]
        stops = plan_fuel_stops(candidates, total_miles=700, range_miles=500, mpg=10)
        ids = [s.station.opis_id for s in stops]
        self.assertEqual(ids[0], 2)
        self.assertNotIn(1, ids)

    def test_fills_when_no_cheaper_station_is_ahead(self):
        candidates = [
            _candidate(1, 400, 2.10),
            _candidate(2, 800, 2.10),
            _candidate(3, 1200, 2.10),
        ]
        stops = plan_fuel_stops(candidates, total_miles=1500, range_miles=500, mpg=10)
        self.assertGreaterEqual(len(stops), 2)
        gaps = [stops[0].miles_from_start]
        gaps.extend(b.miles_from_start - a.miles_from_start for a, b in zip(stops, stops[1:]))
        gaps.append(1500 - stops[-1].miles_from_start)
        self.assertTrue(all(gap <= 500 + 1e-6 for gap in gaps))

    def test_raises_when_gap_exceeds_range(self):
        candidates = [_candidate(1, 100, 3.0), _candidate(2, 800, 3.0)]
        with self.assertRaises(InfeasibleFuelPlanError):
            plan_fuel_stops(candidates, total_miles=1200, range_miles=500, mpg=10)
