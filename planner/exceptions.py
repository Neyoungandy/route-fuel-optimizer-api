class PlannerError(Exception):
    status_code = 500
    code = "planner_error"

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class LocationNotFoundError(PlannerError):
    status_code = 400
    code = "location_not_found"


class RouteNotFoundError(PlannerError):
    status_code = 422
    code = "route_not_found"


class UpstreamServiceError(PlannerError):
    status_code = 502
    code = "upstream_unavailable"


class InfeasibleFuelPlanError(PlannerError):
    status_code = 422
    code = "infeasible_fuel_plan"
