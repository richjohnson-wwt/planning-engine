from datetime import timedelta, date
from typing import List
import math
from .models import PlanRequest, CalendarPlanResult, Site, TeamDay
from .ortools_solver import solve_single_day_vrptw, _convert_solution_to_team_days
from ._internal.utils import calculate_distance_matrix


def _remove_assigned_sites(
    sites_remaining: List[Site],
    team_days: List[TeamDay],
) -> None:
    assigned_ids = {
        site_id
        for td in team_days
        for site_id in td.site_ids
    }
    sites_remaining[:] = [
        s for s in sites_remaining if s.id not in assigned_ids
    ]


def _attach_date(team_days: List[TeamDay], d: date) -> None:
    for td in team_days:
        td.date = d


def _is_non_working_day(d: date, holidays: List[date]) -> bool:
    return d.weekday() >= 5 or d in holidays


def _count_working_days(
    start: date,
    end: date,
    holidays: List[date],
) -> int:
    d = start
    count = 0
    while d <= end:
        if not _is_non_working_day(d, holidays):
            count += 1
        d += timedelta(days=1)
    return count


def greedy_estimate_crews(
    sites: List[Site],
    days: int,
    max_route_minutes: int,
    service_minutes_per_site: int,
    avg_travel_minutes: int = 15,
) -> int:
    per_site = service_minutes_per_site + avg_travel_minutes
    total_minutes = len(sites) * per_site

    capacity_per_crew = days * max_route_minutes
    return max(1, math.ceil(total_minutes / capacity_per_crew))


def plan_fixed_crews(request: PlanRequest) -> CalendarPlanResult:
    crews = request.num_crews_available
    assert crews is not None

    sites_remaining: List[Site] = list(request.sites)
    team_days: List[TeamDay] = []

    current_date = request.start_date or date.today()
    planning_days_used = 0

    while sites_remaining:
        if _is_non_working_day(current_date, request.holidays):
            current_date += timedelta(days=1)
            continue

        # Create depot and prepare sites with indices
        if sites_remaining:
            avg_lat = sum(s.lat for s in sites_remaining) / len(sites_remaining)
            avg_lon = sum(s.lon for s in sites_remaining) / len(sites_remaining)
        else:
            avg_lat, avg_lon = 0.0, 0.0
        
        depot_site = Site(
            id="DEPOT",
            name="DEPOT",
            lat=avg_lat,
            lon=avg_lon,
            service_minutes=0,
            index=0
        )
        
        sites_with_depot = [depot_site] + sites_remaining
        for idx, site in enumerate(sites_with_depot):
            site.index = idx
        
        # Calculate distance matrix
        distance_matrix_minutes = calculate_distance_matrix(sites_with_depot)
        
        # Solve for this day
        solution = solve_single_day_vrptw(
            sites=sites_with_depot,
            request=request,
            distance_matrix_minutes=distance_matrix_minutes,
        )

        if not solution or solution.get("unassigned", 0) == len(sites_remaining):
            raise RuntimeError(
                f"No progress possible with {crews} crews"
            )

        # Convert solution to TeamDay objects
        day_team_days = _convert_solution_to_team_days(solution, sites_with_depot)
        
        _attach_date(day_team_days, current_date)
        team_days.extend(day_team_days)

        _remove_assigned_sites(sites_remaining, day_team_days)

        planning_days_used += 1
        current_date += timedelta(days=1)

    return CalendarPlanResult(
        start_date=request.start_date or date.today(),
        end_date=current_date - timedelta(days=1),
        team_days=team_days,
        unassigned=0,
        crews_used=crews,
        planning_days_used=planning_days_used,
    )

def plan_fixed_calendar(request: PlanRequest) -> CalendarPlanResult:
    assert request.start_date
    assert request.end_date

    planning_days = _count_working_days(
        request.start_date,
        request.end_date,
        request.holidays,
    )

    estimated_crews = greedy_estimate_crews(
        sites=request.sites,
        days=planning_days,
        max_route_minutes=request.max_route_minutes,
        service_minutes_per_site=request.service_minutes_per_site,
    )

    MAX_CREW_BUFFER = 5

    for crews in range(estimated_crews, estimated_crews + MAX_CREW_BUFFER):
        feasible = _validate_calendar_feasibility(
            request,
            crews,
            planning_days,
        )

        if feasible:
            return plan_fixed_crews(
                request.model_copy(
                    update={"num_crews_available": crews}
                )
            )

    raise RuntimeError(
        "Unable to plan within fixed date range"
    )

def _validate_calendar_feasibility(
    request: PlanRequest,
    crews: int,
    planning_days: int,
) -> bool:
    sites_remaining: List[Site] = list(request.sites)

    # Create a copy with updated crews and enable fast_mode for feasibility checks
    # Fast mode is appropriate here since we only need to know if a solution exists,
    # not optimize it
    request_copy = request.model_copy(update={
        "num_crews_available": crews,
        "fast_mode": True
    })

    for _ in range(planning_days):
        if not sites_remaining:
            return True

        # Create depot and prepare sites with indices
        if sites_remaining:
            avg_lat = sum(s.lat for s in sites_remaining) / len(sites_remaining)
            avg_lon = sum(s.lon for s in sites_remaining) / len(sites_remaining)
        else:
            avg_lat, avg_lon = 0.0, 0.0
        
        depot_site = Site(
            id="DEPOT",
            name="DEPOT",
            lat=avg_lat,
            lon=avg_lon,
            service_minutes=0,
            index=0
        )
        
        sites_with_depot = [depot_site] + sites_remaining
        for idx, site in enumerate(sites_with_depot):
            site.index = idx
        
        distance_matrix_minutes = calculate_distance_matrix(sites_with_depot)

        solution = solve_single_day_vrptw(
            sites=sites_with_depot,
            request=request_copy,
            distance_matrix_minutes=distance_matrix_minutes,
        )

        if not solution or solution.get("unassigned", 0) == len(sites_remaining):
            return False

        day_team_days = _convert_solution_to_team_days(solution, sites_with_depot)
        
        _remove_assigned_sites(
            sites_remaining,
            day_team_days,
        )

    return not sites_remaining
