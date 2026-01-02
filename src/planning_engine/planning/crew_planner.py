"""Fixed crew planning: plan with a fixed number of crews over flexible dates."""

from datetime import timedelta, date
from typing import List
from ..models import PlanRequest, CalendarPlanResult, Site, TeamDay
from ..core.depot import create_virtual_depot
from ..solver.solver_utils import prepare_sites_with_indices, calculate_distance_matrix
from ..solver.ortools_solver import solve_single_day_vrptw, _convert_solution_to_team_days


def _remove_assigned_sites(sites_remaining: List[Site], team_days: List[TeamDay]) -> None:
    """Remove sites that have been assigned from the remaining sites list."""
    assigned_ids = {
        site_id
        for td in team_days
        for site_id in td.site_ids
    }
    sites_remaining[:] = [s for s in sites_remaining if s.id not in assigned_ids]


def _attach_date(team_days: List[TeamDay], d: date) -> None:
    """Attach a date to all team days."""
    for td in team_days:
        td.date = d


def _is_non_working_day(d: date, holidays: List[date]) -> bool:
    """Check if a date is a non-working day (weekend or holiday)."""
    return d.weekday() >= 5 or d in holidays


def plan_fixed_crews(request: PlanRequest) -> CalendarPlanResult:
    """
    Plan routes with a fixed number of crews over flexible dates.
    
    Schedules sites across as many working days as needed using the specified
    number of crews. Skips weekends and holidays.
    
    Args:
        request: Planning request with sites, crew count, and constraints
        
    Returns:
        CalendarPlanResult with scheduled routes and date range
        
    Raises:
        RuntimeError: If planning fails or exceeds safety limits
    """
    crews = request.team_config.teams
    sites_remaining: List[Site] = list(request.sites)
    infeasible_sites: List[Site] = []
    team_days: List[TeamDay] = []

    current_date = request.start_date or date.today()
    planning_days_used = 0
    consecutive_no_progress_days = 0
    
    # Safety limits to prevent infinite loops
    MAX_PLANNING_DAYS = 365
    MAX_CONSECUTIVE_NO_PROGRESS = 5

    while sites_remaining and planning_days_used < MAX_PLANNING_DAYS:
        # Skip non-working days
        if _is_non_working_day(current_date, request.holidays):
            current_date += timedelta(days=1)
            continue

        # Create virtual depot and prepare sites
        depot = create_virtual_depot(sites_remaining)
        sites_with_depot = prepare_sites_with_indices(sites_remaining, depot)
        
        # Calculate distance matrix
        distance_matrix_minutes = calculate_distance_matrix(sites_with_depot)
        
        # Solve for this day
        solution = solve_single_day_vrptw(
            sites=sites_with_depot,
            request=request,
            distance_matrix_minutes=distance_matrix_minutes,
        )

        sites_scheduled_today = solution.get("total_sites_scheduled", 0) if solution else 0
        
        if not solution or sites_scheduled_today == 0:
            # No progress made on this day
            consecutive_no_progress_days += 1
            
            if consecutive_no_progress_days >= MAX_CONSECUTIVE_NO_PROGRESS:
                # Identify infeasible sites: those whose service time alone exceeds max_route_minutes
                for site in sites_remaining:
                    if site.service_minutes > request.max_route_minutes:
                        infeasible_sites.append(site)
                
                # Remove infeasible sites from remaining
                sites_remaining = [s for s in sites_remaining if s.service_minutes <= request.max_route_minutes]
                
                if not sites_remaining:
                    # All remaining sites are infeasible
                    break
                
                # If we still have feasible sites but can't schedule them, raise error
                if sites_remaining:
                    unassigned = solution.get("unassigned", len(sites_remaining)) if solution else len(sites_remaining)
                    
                    error_msg = (
                        f"No progress possible with {crews} crews after {consecutive_no_progress_days} consecutive days.\n"
                        f"Sites remaining: {len(sites_remaining)}, "
                        f"Sites scheduled today: {sites_scheduled_today}, "
                        f"Unassigned: {unassigned}.\n"
                        f"Infeasible sites detected: {len(infeasible_sites)}\n"
                        f"Suggestions:\n"
                        f"  - Try disabling 'Fast Mode' for better optimization\n"
                        f"  - Increase 'Max Route Minutes' (current: {request.max_route_minutes})\n"
                        f"  - Decrease 'Service Minutes per Site' (current: {request.service_minutes_per_site})\n"
                        f"  - Increase number of teams/crews (current: {crews})"
                    )
                    raise RuntimeError(error_msg)
        else:
            # Progress made, reset counter
            consecutive_no_progress_days = 0
            
            # Convert solution to TeamDay objects
            day_team_days = _convert_solution_to_team_days(solution, sites_with_depot, request.break_minutes)
            
            _attach_date(day_team_days, current_date)
            team_days.extend(day_team_days)

            _remove_assigned_sites(sites_remaining, day_team_days)

        planning_days_used += 1
        current_date += timedelta(days=1)

    if planning_days_used >= MAX_PLANNING_DAYS:
        raise RuntimeError(
            f"Planning exceeded maximum limit of {MAX_PLANNING_DAYS} days. "
            f"Sites remaining: {len(sites_remaining)}. "
            f"Consider increasing crew count or adjusting constraints."
        )

    return CalendarPlanResult(
        start_date=request.start_date or date.today(),
        end_date=current_date - timedelta(days=1),
        team_days=team_days,
        unassigned=len(infeasible_sites),
        crews_used=crews,
        planning_days_used=planning_days_used,
    )
