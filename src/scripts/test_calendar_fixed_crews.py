from datetime import date, time

from planning_engine.calendar_wrapper import plan_fixed_crews
from planning_engine.models import PlanRequest, Site, TeamConfig, Workday

def make_sites(n: int) -> list[Site]:
    sites = []
    for i in range(n):
        sites.append(
            Site(
                id=str(1000 + i),
                name=f"Site {i}",
                lat=38.6 + i * 0.01,
                lon=-90.2 + i * 0.01,
                service_minutes=60,
            )
        )
    return sites

def main():
    sites = make_sites(10)
    request = PlanRequest(
        workspace="fixed_crews_calendar",
        sites=sites,
        team_config=TeamConfig(teams=10, workday=Workday(start=time(8), end=time(17))),
        num_crews_available=3,
        max_route_minutes=480,
        service_minutes_per_site=60,
        fast_mode=True,
    )

    result = plan_fixed_crews(request)

    print("\n=== FIXED CREWS SMOKE TEST ===")
    print(f"Crews used: {result.crews_used}")
    print(f"Planning days used: {result.planning_days_used}")
    print(f"Team-days produced: {len(result.team_days)}")
    
    # ---- Assertions ----
    
    # 1. Correct number of crews used
    assert result.crews_used == 3, f"Expected 3 crews, got {result.crews_used}"
    
    # 2. All sites assigned
    assigned = [
        site_id
        for td in result.team_days
        for site_id in td.site_ids
    ]
    assert len(assigned) == len(sites), f"Not all sites assigned: {len(assigned)}/{len(sites)}"
    
    # 3. No duplicate visits
    assert len(set(assigned)) == len(assigned), "Duplicate site visits detected"
    
    # 4. No unassigned sites
    assert result.unassigned == 0, f"Unassigned sites remain: {result.unassigned}"
    
    # 5. All team_days have dates assigned
    for td in result.team_days:
        assert td.date is not None, f"Team {td.team_id} has no date assigned"
    
    # 6. Date range is valid
    assert result.start_date <= result.end_date, "Invalid date range"
    
    # 7. Planning days used is positive
    assert result.planning_days_used > 0, "No planning days used"
    
    # 8. Each team_day respects max_route_minutes
    for td in result.team_days:
        assert td.route_minutes <= request.max_route_minutes, \
            f"Team {td.team_id} exceeds max route minutes: {td.route_minutes} > {request.max_route_minutes}"
    
    # 9. Service minutes are reasonable
    for td in result.team_days:
        assert td.service_minutes > 0, f"Team {td.team_id} has no service minutes"
    
    print("✓ All assertions passed!")


if __name__ == "__main__":
    main()