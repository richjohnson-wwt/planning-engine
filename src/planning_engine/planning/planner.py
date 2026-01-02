"""Main planning orchestration - routes requests to appropriate planning strategy."""

from ..models import PlanRequest, PlanResult
from ..core.validation import validate_plan_request
from ..core.site_loader import load_sites_from_geocoded
from .cluster_planner import plan_with_clusters
from .calendar_planner import plan_fixed_calendar
from .crew_planner import plan_fixed_crews


def execute_plan(request: PlanRequest) -> PlanResult:
    """
    Execute route planning based on request parameters.
    
    Routes to appropriate planning strategy:
    - Cluster-based if use_clusters=True
    - Fixed calendar if start_date and end_date provided
    - Fixed crews otherwise
    
    Args:
        request: Planning request with sites and constraints
        
    Returns:
        PlanResult with optimized routes
        
    Raises:
        ValueError: If request validation fails
        FileNotFoundError: If required workspace files don't exist
    """
    # Validate request
    validate_plan_request(request)
    
    # Handle cluster-based planning
    if request.use_clusters:
        return plan_with_clusters(request)
    
    # Load sites from geocoded.csv if not provided
    if request.sites is None:
        request.sites = load_sites_from_geocoded(
            request.workspace,
            request.state_abbr,
            request.service_minutes_per_site
        )
    
    # Validate we have sites to plan
    if not request.sites:
        raise ValueError(
            f"No sites found for workspace '{request.workspace}'"
            + (f" with state '{request.state_abbr}'" if request.state_abbr else "")
        )
    
    # Determine planning mode based on date parameters
    if request.start_date and request.end_date:
        # Fixed calendar mode: find minimum crews for date range
        calendar_result = plan_fixed_calendar(request)
        return calendar_result.to_plan_result()
    else:
        # Fixed crew mode: schedule over flexible dates
        calendar_result = plan_fixed_crews(request)
        return calendar_result.to_plan_result()
