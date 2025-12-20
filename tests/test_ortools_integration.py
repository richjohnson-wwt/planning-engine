from planning_engine import plan
from planning_engine.models import PlanRequest, Site, TeamConfig, Workday
from datetime import time, date

def test_plan_with_ortools_simple():
    """Test that OR-Tools solver is invoked when date range is provided."""
    # GIVEN: A team config with 2 teams
    team_config = TeamConfig(
        teams=2,
        workday=Workday(start=time(hour=8, minute=0), end=time(hour=17, minute=0))
    )
    
    # AND: A list of sites with coordinates
    sites = [
        Site(id="A", name="Site A", lat=38.6270, lon=-90.1994, service_minutes=60),
        Site(id="B", name="Site B", lat=38.6400, lon=-90.2500, service_minutes=60),
        Site(id="C", name="Site C", lat=38.6500, lon=-90.2000, service_minutes=60),
    ]
    
    # AND: A plan request with OR-Tools specific fields
    req = PlanRequest(
        workspace="test_workspace",
        sites=sites,
        team_config=team_config,
        start_date=date(2025, 1, 1),
        end_date=date(2025, 1, 2),
        num_crews_available=2,
        max_route_minutes=480,
        holidays=[],
        fast_mode=True
    )

    # WHEN: We run the planning engine
    result = plan(req)

    # THEN: The result should have team days with scheduled sites
    assert len(result.team_days) > 0
    assert all(len(td.site_ids) > 0 for td in result.team_days)
    
    # AND: All sites should be assigned
    all_assigned_sites = set()
    for td in result.team_days:
        all_assigned_sites.update(td.site_ids)
    assert all_assigned_sites == {"A", "B", "C"}


def test_plan_without_ortools_fallback():
    """Test that simple assignment is used when date range is not provided."""
    # GIVEN: A team config
    team_config = TeamConfig(
        teams=1,
        workday=Workday(start=time(hour=8, minute=0), end=time(hour=17, minute=0))
    )
    
    # AND: A list of sites
    sites = [
        Site(id="A", name="Site A", lat=38.6270, lon=-90.1994, service_minutes=30),
        Site(id="B", name="Site B", lat=38.6400, lon=-90.2500, service_minutes=45),
    ]
    
    # AND: A plan request WITHOUT OR-Tools fields (no start_date/end_date)
    req = PlanRequest(
        workspace="test_workspace",
        sites=sites,
        team_config=team_config,
        fast_mode=True
    )

    # WHEN: We run the planning engine
    result = plan(req)

    # THEN: The result should use simple assignment (all sites to team 1)
    assert len(result.team_days) == 1
    assert result.team_days[0].team_id == 1
    assert set(result.team_days[0].site_ids) == {"A", "B"}
