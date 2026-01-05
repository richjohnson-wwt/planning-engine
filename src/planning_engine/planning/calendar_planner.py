"""Fixed calendar planning: find minimum crews needed for a fixed date range."""

from datetime import timedelta, date
from typing import List
import math
from ..models import PlanRequest, CalendarPlanResult, Site, TeamDay
from ..core.depot import create_virtual_depot
from ..solver.solver_utils import prepare_sites_with_indices, calculate_distance_matrix
from ..solver.ortools_solver import solve_single_day_vrptw, _convert_solution_to_team_days
from .crew_planner import _remove_assigned_sites


def _count_working_days(start: date, end: date, holidays: List[date]) -> int:
    """Count working days (excluding weekends and holidays) in a date range."""
    d = start
    count = 0
    while d <= end:
        if d.weekday() < 5 and d not in holidays:  # Not weekend or holiday
            count += 1
        d += timedelta(days=1)
    return count


def _estimate_crews_needed(
    sites: List[Site],
    days: int,
    max_route_minutes: int,
    service_minutes_per_site: int,
    avg_travel_minutes: int = 15,
) -> int:
    """
    Estimate minimum number of crews needed to complete all sites in given days.
    
    Uses a greedy estimation based on total work and available capacity.
    """
    per_site = service_minutes_per_site + avg_travel_minutes
    total_minutes = len(sites) * per_site

    capacity_per_crew = days * max_route_minutes
    return max(1, math.ceil(total_minutes / capacity_per_crew))


def _validate_calendar_feasibility(
    request: PlanRequest,
    crews: int,
    planning_days: int,
) -> bool:
    """
    Check if a given number of crews can complete all sites within the date range.
    
    Uses fast mode for quick feasibility checks without full optimization.
    """
    sites_remaining: List[Site] = list(request.sites)

    # Create a copy with updated crews and enable fast_mode for feasibility checks
    updated_team_config = request.team_config.model_copy(update={"teams": crews})
    request_copy = request.model_copy(update={
        "team_config": updated_team_config,
        "fast_mode": True
    })

    for _ in range(planning_days):
        if not sites_remaining:
            return True

        # Create virtual depot and prepare sites
        depot = create_virtual_depot(sites_remaining)
        sites_with_depot = prepare_sites_with_indices(sites_remaining, depot)
        
        # Calculate distance matrix
        distance_matrix_minutes = calculate_distance_matrix(sites_with_depot)
        
        # Solve for this day
        solution = solve_single_day_vrptw(
            sites=sites_with_depot,
            request=request_copy,
            distance_matrix_minutes=distance_matrix_minutes,
        )

        if not solution or solution.get("total_sites_scheduled", 0) == 0:
            return False

        # Convert and remove assigned sites
        day_team_days = _convert_solution_to_team_days(solution, sites_with_depot, request_copy.break_minutes)
        _remove_assigned_sites(sites_remaining, day_team_days)

    return len(sites_remaining) == 0


def plan_fixed_calendar(request: PlanRequest) -> CalendarPlanResult:
    """
    Plan routes with a fixed date range, finding minimum crews needed.
    
    Iteratively tries increasing crew counts until all sites can be scheduled
    within the specified date range.
    
    Args:
        request: Planning request with start_date, end_date, sites, and constraints
        
    Returns:
        CalendarPlanResult with scheduled routes and crew count
        
    Raises:
        RuntimeError: If unable to find feasible crew count
        AssertionError: If start_date or end_date not provided
    """
    assert request.start_date, "start_date is required for fixed calendar mode"
    assert request.end_date, "end_date is required for fixed calendar mode"

    planning_days = _count_working_days(
        request.start_date,
        request.end_date,
        request.holidays,
    )

    # Account for break time when estimating crews
    effective_route_minutes = request.max_route_minutes - request.break_minutes
    
    estimated_crews = _estimate_crews_needed(
        sites=request.sites,
        days=planning_days,
        max_route_minutes=effective_route_minutes,
        service_minutes_per_site=request.service_minutes_per_site,
    )

    # In fixed calendar mode, we need to find however many crews it takes
    # to complete all work within the date range. Set a reasonable upper limit.
    MAX_CREW_BUFFER = max(50, estimated_crews * 2)

    for crews in range(estimated_crews, estimated_crews + MAX_CREW_BUFFER):
        feasible = _validate_calendar_feasibility(
            request,
            crews,
            planning_days,
        )

        if feasible:
            # Update team_config with the calculated number of crews
            updated_team_config = request.team_config.model_copy(update={"teams": crews})
            
            # Import here to avoid circular dependency
            from .crew_planner import plan_fixed_crews
            
            try:
                # Try to plan with this crew count
                result = plan_fixed_crews(
                    request.model_copy(
                        update={"team_config": updated_team_config}
                    )
                )
                
                # Verify all sites were scheduled within the date range
                if result.unassigned == 0 and result.end_date <= request.end_date:
                    return result
                    
                # If not all sites scheduled or exceeded date range, try more crews
                continue
                
            except RuntimeError as e:
                # If planning failed with this crew count, try more crews
                # Only raise if we've exhausted all crew options
                if crews >= estimated_crews + MAX_CREW_BUFFER - 1:
                    raise RuntimeError(
                        f"Unable to plan within fixed date range even with {crews} crews. "
                        f"Original error: {str(e)}"
                    )
                continue

    raise RuntimeError(
        f"Unable to plan within fixed date range. "
        f"Tried {estimated_crews} to {estimated_crews + MAX_CREW_BUFFER - 1} crews "
        f"for {len(request.sites)} sites over {planning_days} working days. "
        f"Consider: increasing date range, reducing service time, or enabling fast mode."
    )
