from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from rest_framework.test import APIRequestFactory

from planner.models import DrivingRoute, FuelPlan, FuelPurchase, GeoPoint, RoutePoint, Station
from planner.views import RoutePlanView


def _sample_plan() -> FuelPlan:
    start = GeoPoint(32.7767, -96.7970, "Dallas, TX", "Dallas, Texas, United States")
    finish = GeoPoint(41.8781, -87.6298, "Chicago, IL", "Chicago, Illinois, United States")
    station = Station(
        opis_id=44,
        name="CIRCLE K",
        address="I-35",
        city="Jarrell",
        state="TX",
        retail_price=2.919,
        latitude=30.82,
        longitude=-97.60,
    )
    route = DrivingRoute(
        distance_miles=925.0,
        duration_seconds=50000,
        geometry=[[-96.8, 32.8], [-87.6, 41.9]],
        samples=[
            RoutePoint(32.8, -96.8, 0.0),
            RoutePoint(41.9, -87.6, 925.0),
        ],
    )
    purchase = FuelPurchase(station=station, miles_from_start=410.0, gallons=12.5, cost_usd=36.49)
    return FuelPlan(
        start=start,
        finish=finish,
        route=route,
        stops=[purchase],
        gallons_consumed=92.5,
        gallons_purchased=12.5,
        total_fuel_cost_usd=36.49,
    )


@override_settings(ROOT_URLCONF="config.urls")
class RoutePlanApiTests(SimpleTestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = RoutePlanView.as_view()

    def test_rejects_identical_endpoints(self):
        request = self.factory.post(
            "/api/v1/routes/plan/",
            {"start": "Dallas, TX", "finish": "Dallas, TX"},
            format="json",
        )
        response = self.view(request)
        self.assertEqual(response.status_code, 400)

    @patch("planner.views.build_fuel_plan")
    def test_returns_route_and_cost(self, mocked_plan):
        mocked_plan.return_value = _sample_plan()
        request = self.factory.post(
            "/api/v1/routes/plan/",
            {"start": "Dallas, TX", "finish": "Chicago, IL"},
            format="json",
        )
        response = self.view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["fuel"]["total_fuel_cost_usd"], 36.49)
        self.assertEqual(response.data["route"]["geometry"]["type"], "LineString")
        self.assertEqual(len(response.data["fuel"]["stops"]), 1)
