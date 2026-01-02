"""Request validation utilities."""

from ..models import PlanRequest


def validate_plan_request(request: PlanRequest) -> None:
    """
    Validate a PlanRequest has required fields based on planning mode.
    
    Args:
        request: PlanRequest to validate
        
    Raises:
        ValueError: If required fields are missing or invalid
    """
    # If using clusters, state_abbr is required
    if request.use_clusters and not request.state_abbr:
        raise ValueError(
            "state_abbr is required when use_clusters is True. "
            "Specify which state's clusters to load (e.g., 'LA', 'NC')"
        )
    
    # If sites not provided, need workspace and state_abbr to load them
    if request.sites is None:
        if not request.workspace:
            raise ValueError("workspace is required when sites are not provided")
        if not request.state_abbr:
            raise ValueError(
                "state_abbr is required when sites are not provided. "
                "Specify which state's sites to load (e.g., 'LA', 'NC')"
            )
    
    # Validate we have sites to plan (either provided or will be loaded)
    # Exception: if using clusters, sites will be loaded from clustered.csv
    if request.sites is not None and len(request.sites) == 0 and not request.use_clusters:
        raise ValueError("Cannot plan with zero sites")
    
    # Calendar mode requires both start and end dates
    # Crew mode can have start_date without end_date (flexible end)
    # Only validate if end_date is provided without start_date
    if request.end_date is not None and request.start_date is None:
        raise ValueError(
            "start_date is required when end_date is provided"
        )
