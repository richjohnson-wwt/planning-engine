from pydantic import BaseModel
from typing import List
from datetime import time

class Site(BaseModel):
    id: str
    lat: float
    lon: float
    service_minutes: int

class Workday(BaseModel):
    start: time
    end: time
    
class TeamConfig(BaseModel):
    teams: int
    workday: Workday

class TeamDay(BaseModel):
    team_id: int
    site_ids: List[str]
    total_minutes: int

class PlanRequest(BaseModel):
    workspace: str
    sites: List[Site]
    team_config: TeamConfig


class PlanResult(BaseModel):
    team_days: List[TeamDay]
