from datetime import date, time
from planning_engine.models import Site, Workday, TeamConfig, PlanRequest
from planning_engine.ortools_solver import plan_routes

# This will immediately surface:

# Over-scheduling

# Bad time math

# Routes ignoring daily limits

def main():
    sites = [
        Site(
            id=str(i),
            name=f"Site {i}",
            lat=30.4 + i * 0.01,
            lon=-91.1,
            service_minutes=90,  # heavy work
        )
        for i in range(15)
    ]

    request = PlanRequest(
        workspace="pressure-test",
        sites=sites,
        team_config=TeamConfig(
            teams=2,
            workday=Workday(
                start=time(9, 0),
                end=time(17, 0),
            ),
        ),
        start_date=date(2025, 1, 6),
        end_date=date(2025, 1, 6),
        num_crews_available=2,  # Hard limit: only 2 crews available
        max_route_minutes=360,  # 6 hours
        service_minutes_per_site=90,
    )

    result = plan_routes(request)

    total_sites = sum(len(td.site_ids) for td in result.team_days)

    print(f"\nScheduled {total_sites}/{len(sites)} sites")
    print(f"Unassigned: {result.unassigned}")

    for td in result.team_days:
        print(
            f"Team {td.team_id}: "
            f"{len(td.site_ids)} sites, "
            f"service={td.service_minutes}, "
            f"route={td.route_minutes}"
        )

    # Assertions for time pressure scenario
    assert total_sites <= len(sites), "Cannot schedule more sites than available"
    assert len(result.team_days) <= request.get_num_crews(), "Cannot use more crews than available"
    
    # With 2 crews and 360 min limit, we can fit ~8 sites max (4 per crew)
    # So we expect some sites to be unassigned
    expected_max_sites = 2 * (360 // 90)  # 2 crews * 4 sites per crew = 8
    assert total_sites <= expected_max_sites, f"Scheduled too many sites: {total_sites} > {expected_max_sites}"
    assert result.unassigned > 0, "Expected some sites to be unassigned due to time pressure"

    for td in result.team_days:
        assert td.route_minutes <= request.max_route_minutes, f"Route exceeds max: {td.route_minutes} > {request.max_route_minutes}"
        assert td.route_minutes >= td.service_minutes, "Route time should be >= service time"

    print(f"\n✅ Time pressure test PASSED")
    print(f"   Successfully handled constraint: {total_sites} sites scheduled, {result.unassigned} unassigned")


if __name__ == "__main__":
    main()
