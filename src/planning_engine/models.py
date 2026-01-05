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
    address: Optional[str] = None  # Full address for display and mapping
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
    sites: Optional[List['Site']] = None  # Full site objects for mapping/visualization

    # Pure labor time
    service_minutes: int

    # Pure travel time (driving between sites)
    travel_minutes: int

    # Actual route consumption (travel + service + slack)
    route_minutes: int
    
    # Break time allocated for this team-day
    break_minutes: int = 0
    
    # Optional date field for multi-day scheduling
    date: Optional[date] = None
    
    # Optional cluster ID for clustered planning (for UI display, 0-based internally)
    cluster_id: Optional[int] = None
    
    # Optional team label for display (e.g., "C1-T1" for cluster 1, team 1)
    team_label: Optional[str] = None
    
    model_config = {
        "json_schema_serialization_defaults_required": True
    }


class PlanRequest(BaseModel):
    """Plan request model for single-day VRP optimization.
    
    CURRENT IMPLEMENTATION (Single-Day VRP):
    - Optimizes routes for ONE day only
    - start_date: Used for timestamp reporting (e.g., "route for Jan 15, 2025")
    - end_date: Reserved for future multi-day scheduling (currently not used)
    - holidays: Reserved for future multi-day scheduling (currently not used)
    
    FUTURE FEATURES (Not Yet Implemented):
    - Multi-day scheduling across date range (start_date to end_date)
    - Exclude holidays and blackout dates from schedule
    - Estimate total project duration
    - See multi_day_scheduler.py for roadmap
    
    Sites can be provided in two ways:
    1. Explicitly via 'sites' field (for direct API calls)
    2. Auto-loaded from geocoded.csv via 'state_abbr' (workspace must have geocoded.csv)
    
    For cluster-based planning, set use_clusters=True to plan each geographic cluster separately.
    """
    workspace: str
    sites: Optional[List[Site]] = None  # Optional: can be auto-loaded from geocoded.csv
    team_config: TeamConfig
    
    # Filtering options
    state_abbr: Optional[str] = None  # Filter sites by state abbreviation (e.g., "LA", "NC")
    use_clusters: bool = False  # If True, load from clustered.csv and plan each cluster separately
    
    # OR-Tools solver specific fields
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    max_route_minutes: int = 480  # 8 hours default
    break_minutes: int = 30
    holidays: List[date] = Field(default_factory=list)
    service_minutes_per_site: int = 60
    fast_mode: bool = False  # If True, use faster but less optimal solver settings

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "workspace": "foo",
                    "sites": None,
                    "team_config": {
                        "teams": 1,
                        "workday": {
                            "start": "08:00:00",
                            "end": "17:00:00"
                        }
                    },
                    "state_abbr": "LA",
                    "use_clusters": True,
                    "start_date": "2025-01-01",
                    "end_date": "2025-01-31",
                    "max_route_minutes": 480,
                    "break_minutes": 30,
                    "holidays": [],
                    "service_minutes_per_site": 60,
                    "fast_mode": True
                }
            ]
        }
    }
    
    def get_num_crews(self) -> int:
        """Get number of crews from team_config."""
        return self.team_config.teams


class PlanResult(BaseModel):
    team_days: List[TeamDay]
    unassigned: int = 0  # number of sites not scheduled
    start_date: Optional[date] = None  # Actual start date used in planning
    end_date: Optional[date] = None  # Calculated end date (for fixed crew mode)

class CalendarPlanResult(BaseModel):
    start_date: date
    end_date: date
    team_days: List[TeamDay]
    unassigned: int
    crews_used: int
    planning_days_used: int

    def to_plan_result(self) -> PlanResult:
        return PlanResult(
            team_days=self.team_days,
            unassigned=self.unassigned,
            start_date=self.start_date,
            end_date=self.end_date,
        )
