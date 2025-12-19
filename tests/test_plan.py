from planning_engine import plan
from planning_engine.models import PlanRequest, Site, TeamConfig, Workday
from datetime import time

def test_plan_counts_sites():
    # GIVEN: A team config with 1 team and a workday from 8:00 to 17:00
    team_config = TeamConfig(
        teams=1,
        workday=Workday(start=time(hour=8, minute=0), end=time(hour=17, minute=0))
    )
    
    # AND: A list of sites with service minutes
    req = PlanRequest(
        workspace="test_workspace",
        sites = [
            Site(id="A", lat=38.6270, lon=-90.1994, service_minutes=30),
            Site(id="B", lat=38.6400, lon=-90.2500, service_minutes=45),
        ],
        team_config=team_config
    )

    # WHEN: We run the planning engine
    result = plan(req)

    # THEN: The result should have 1 team day
    assert result.team_days[0].team_id == 1
