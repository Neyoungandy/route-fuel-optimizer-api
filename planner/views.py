from rest_framework.response import Response
from rest_framework.views import APIView

from planner.exceptions import PlannerError
from planner.serializers import RoutePlanRequestSerializer
from planner.services.plan import build_fuel_plan, serialize_plan
from planner.services.stations import station_count


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        return Response(
            {
                "status": "ok",
                "stations_loaded": station_count(),
            }
        )


class RoutePlanView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        serializer = RoutePlanRequestSerializer(data=request.query_params)
        return self._respond(serializer)

    def post(self, request):
        serializer = RoutePlanRequestSerializer(data=request.data)
        return self._respond(serializer)

    def _respond(self, serializer: RoutePlanRequestSerializer):
        serializer.is_valid(raise_exception=True)
        try:
            plan = build_fuel_plan(
                serializer.validated_data["start"],
                serializer.validated_data["finish"],
            )
        except PlannerError as exc:
            return Response(
                {"error": exc.code, "detail": exc.message},
                status=exc.status_code,
            )
        return Response(serialize_plan(plan))
