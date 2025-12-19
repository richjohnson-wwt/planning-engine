from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import time, date

class Site(BaseModel):
    """Site model compatible with both API and OR-Tools solver.
    
    The 'id' field is used by the API for identification.
    The 'index' field is used by OR-Tools solver for routing.
    """
    id: str
    name: str
    lat: float
    lon: float
    service_minutes: int = 60
    blackout_dates: Optional[List[date]] = None
    index: Optional[int] = None  # Used by OR-Tools solver, set during planning

class Workday(BaseModel):
    start: time
    end: time
    
class TeamConfig(BaseModel):
    teams: int
    workday: Workday

class TeamDay(BaseModel):
    team_id: int
    site_ids: List[str]

    # Pure labor time
    service_minutes: int

    # Actual route consumption (travel + service + slack)
    route_minutes: int


class PlanRequest(BaseModel):
    """Plan request model supporting both simple and advanced routing.
    
    For basic usage: provide workspace, sites (or state_abbr to auto-load), and team_config.
    For OR-Tools solver: also provide start_date, end_date, holidays, etc.
    
    Sites can be provided in two ways:
    1. Explicitly via 'sites' field (for direct API calls)
    2. Auto-loaded from geocoded.csv via 'state_abbr' (workspace must have geocoded.csv)
    """
    workspace: str
    sites: Optional[List[Site]] = None  # Optional: can be auto-loaded from geocoded.csv
    team_config: TeamConfig
    
    # Filtering options
    state_abbr: Optional[str] = None  # Filter sites by state abbreviation (e.g., "LA", "NC")
    
    # OR-Tools solver specific fields
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    num_crews_available: Optional[int] = None  # If not provided, uses team_config.teams
    max_route_minutes: int = 480  # 8 hours default
    break_minutes: int = 30
    holidays: List[date] = Field(default_factory=list)
    max_sites_per_crew_per_day: int = 8
    service_minutes_per_site: int = 60
    minimize_crews: bool = True  # Try to use fewer crews
    
    def get_num_crews(self) -> int:
        """Get number of crews from either num_crews_available or team_config."""
        return self.num_crews_available if self.num_crews_available is not None else self.team_config.teams


class PlanResult(BaseModel):
    team_days: List[TeamDay]
    unassigned: int = 0  # number of sites not scheduled
