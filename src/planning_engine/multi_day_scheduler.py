"""
Multi-Day Scheduler (FUTURE IMPLEMENTATION)

This module will orchestrate multi-day project scheduling by calling the single-day
VRP solver for each work day in the project timeline.

ARCHITECTURE:
    Multi-Day Scheduler (High-Level)
        ↓
    Calculate work days (exclude weekends, holidays)
        ↓
    Allocate sites to days (bin packing, priority)
        ↓
    For each day: Call plan_single_day_vrp()
        ↓
    Combine results into project schedule

CURRENT STATUS: Not implemented - placeholders only
SINGLE-DAY VRP: Fully implemented and production-ready in ortools_solver.py
"""

from datetime import date, timedelta
from typing import List, Optional
from .models import PlanRequest, PlanResult, Site, TeamDay


def plan_multi_day_schedule(request: PlanRequest) -> PlanResult:
    """
    Plan routes across multiple days (start_date to end_date).
    
    This is a HIGH-LEVEL scheduler that orchestrates multiple single-day optimizations.
    For each work day, it calls plan_single_day_vrp() to get optimized routes.
    
    DUAL OPTIMIZATION MODES:
    
    Mode 1: Fixed Crews → Calculate Duration
        - Provide: num_crews_available (fixed)
        - Provide: start_date
        - Omit or set end_date = None
        - Scheduler calculates: How many days needed with fixed crews
        - Example: "With 3 crews, will take 7 days to complete 150 sites"
    
    Mode 2: Fixed Dates → Calculate Crews
        - Provide: start_date and end_date (fixed timeline)
        - Omit or set num_crews_available = None
        - Set minimize_crews = True
        - Scheduler calculates: Minimum crews needed to meet deadline
        - Example: "Need 4 crews to complete 150 sites in 5 days"
    
    Features to implement:
    - Calculate available work days between start_date and end_date
    - Exclude weekends, holidays, and blackout dates
    - Allocate sites to days based on crew capacity
    - Handle site priorities and dependencies
    - Support ramp-up phases (Crawl, Walk, Run)
    - Respect per-site service time variations (T-shirt sizes)
    - Check if regions can be completed before breaks
    
    Args:
        request: Planning request with:
            - start_date: Project start date (required)
            - end_date: Project end date (required for Mode 2, optional for Mode 1)
            - holidays: List of holiday dates to exclude
            - sites: All sites to schedule across the project
            - num_crews_available: Crews available per day (required for Mode 1)
            - minimize_crews: If True, calculate minimum crews needed (Mode 2)
            - Other constraints (max_route_minutes, service_minutes, etc.)
    
    Returns:
        PlanResult with team_days scheduled across multiple days
        
    TODO: Implement this function
    Current workaround: Call plan_single_day_vrp() directly for single-day optimization
    """
    raise NotImplementedError(
        "Multi-day scheduling not yet implemented. "
        "Use plan_single_day_vrp() for single-day route optimization. "
        "See multi_day_scheduler.py for architecture and roadmap."
    )


def calculate_work_days(
    start_date: date,
    end_date: date,
    holidays: List[date],
    exclude_weekends: bool = True
) -> List[date]:
    """
    Calculate available work days in the date range.
    
    Args:
        start_date: Project start date
        end_date: Project end date (inclusive)
        holidays: List of holiday dates to exclude
        exclude_weekends: If True, exclude Saturdays and Sundays
        
    Returns:
        List of work dates (excludes weekends and holidays)
        
    TODO: Implement this function
    """
    raise NotImplementedError("TODO: Implement work day calculation")


def allocate_sites_to_days(
    sites: List[Site],
    work_days: List[date],
    crews_per_day: int,
    max_sites_per_crew_per_day: int,
    strategy: str = "balanced"
) -> dict[date, List[Site]]:
    """
    Allocate sites to specific work days.
    
    Strategies:
    - "balanced": Evenly distribute sites across days
    - "priority": Schedule high-priority sites first
    - "geographic": Group by geographic clusters
    - "ramp": Crawl/Walk/Run approach (fewer sites early, ramp up over time)
    
    Args:
        sites: All sites to schedule
        work_days: Available work days
        crews_per_day: Number of crews available per day
        max_sites_per_crew_per_day: Max sites each crew can handle per day
        strategy: Allocation strategy
        
    Returns:
        Dict mapping each date to list of sites scheduled for that day
        
    TODO: Implement allocation strategies
    """
    raise NotImplementedError("TODO: Implement site allocation logic")


def calculate_crews_needed(
    num_sites: int,
    num_work_days: int,
    sites_per_crew_per_day: int
) -> int:
    """
    Calculate minimum number of crews needed to complete sites in given days.
    
    Used for Mode 2: Fixed Dates → Calculate Crews
    
    Args:
        num_sites: Total number of sites to complete
        num_work_days: Number of work days available
        sites_per_crew_per_day: Sites each crew can complete per day
        
    Returns:
        Minimum number of crews needed (rounded up)
        
    Example:
        150 sites, 5 days, 8 sites/crew/day
        → Need 150 / (5 × 8) = 150 / 40 = 3.75 → 4 crews
        
    TODO: Implement crew calculation
    """
    raise NotImplementedError("TODO: Implement crew calculation")


def estimate_project_duration(
    num_sites: int,
    crews_per_day: int,
    sites_per_crew_per_day: int,
    start_date: date,
    holidays: List[date]
) -> tuple[date, int]:
    """
    Estimate project completion date and number of work days needed.
    
    Used for Mode 1: Fixed Crews → Calculate Duration
    
    Args:
        num_sites: Total number of sites to complete
        crews_per_day: Number of crews available per day
        sites_per_crew_per_day: Sites each crew can complete per day
        start_date: Project start date
        holidays: Holidays to exclude from schedule
        
    Returns:
        Tuple of (estimated_end_date, num_work_days_needed)
        
    Example:
        150 sites, 3 crews, 8 sites/crew/day
        → Capacity: 3 × 8 = 24 sites/day
        → Days needed: 150 / 24 = 6.25 → 7 days
        → End date: start_date + 7 work days (excluding weekends/holidays)
        
    TODO: Implement duration estimation
    """
    raise NotImplementedError("TODO: Implement duration estimation")


def check_region_completion_before_break(
    sites: List[Site],
    break_date: date,
    crews_per_day: int,
    sites_per_crew_per_day: int,
    start_date: date
) -> tuple[bool, Optional[date]]:
    """
    Check if a region can be completed before a scheduled break.
    
    Args:
        sites: Sites in the region
        break_date: Date of the break (holiday, blackout, etc.)
        crews_per_day: Number of crews available
        sites_per_crew_per_day: Sites per crew per day
        start_date: When work would start
        
    Returns:
        Tuple of (can_complete_before_break, estimated_completion_date)
        
    TODO: Implement break analysis
    """
    raise NotImplementedError("TODO: Implement break analysis")


# ============================================================================
# IMPLEMENTATION NOTES FOR FUTURE DEVELOPER
# ============================================================================

"""
IMPLEMENTATION ROADMAP:

Phase 1: Basic Multi-Day Scheduling
- [ ] Implement calculate_work_days() - exclude weekends and holidays
- [ ] Implement allocate_sites_to_days() with "balanced" strategy
- [ ] Implement plan_multi_day_schedule() to call plan_single_day_vrp() for each day
- [ ] Test with simple 3-day, 50-site scenario

Phase 2: Duration Estimation
- [ ] Implement estimate_project_duration()
- [ ] Add capacity calculation (crews × sites/day × work_days)
- [ ] Handle scenarios where capacity < total sites

Phase 3: Advanced Allocation
- [ ] Implement "priority" allocation strategy
- [ ] Implement "geographic" allocation strategy (use existing clusters)
- [ ] Implement "ramp" allocation strategy (Crawl/Walk/Run)

Phase 4: Break Analysis
- [ ] Implement check_region_completion_before_break()
- [ ] Add logic to push work to after break if can't complete before
- [ ] Support multiple breaks in timeline

Phase 5: Variable Service Times
- [ ] Add "t_shirt_size" field to Site model (S, M, L, XL)
- [ ] Map t-shirt sizes to service_minutes (S=30, M=60, L=90, XL=120)
- [ ] Update site loading to respect per-site service times

DEPENDENCIES:
- plan_single_day_vrp() - DONE ✅ (in ortools_solver.py)
- State-based clustering - DONE ✅ (in api.py)
- Geocoding and data prep - DONE ✅

TESTING STRATEGY:
1. Unit tests for each helper function (calculate_work_days, allocate_sites_to_days)
2. Integration test: 3-day project with 50 sites, 3 crews
3. Test with holidays and weekends
4. Test with different allocation strategies
5. Test break scenarios

EXAMPLE USAGE (once implemented):
    request = PlanRequest(
        workspace="foo",
        state_abbr="LA",
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 21),  # 3 weeks
        holidays=[date(2025, 1, 15)],  # MLK Day
        num_crews_available=3,
        max_route_minutes=480,
        service_minutes_per_site=60,
        max_sites_per_crew_per_day=8
    )
    
    # This will:
    # 1. Calculate work days (14 days after excluding weekends + holiday)
    # 2. Allocate ~21 sites per day for 7 days
    # 3. Call plan_single_day_vrp() for each of those 7 days
    # 4. Return combined schedule with 21 team-days
    result = plan_multi_day_schedule(request)
"""
