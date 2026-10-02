from django.urls import path

from planner.views import HealthView, RoutePlanView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("v1/routes/plan/", RoutePlanView.as_view(), name="route-plan"),
]
