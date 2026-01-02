from datetime import date, time

from planning_engine.planning.calendar_planner import plan_fixed_calendar
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
        workspace="smoke_calendar",
        sites=sites,
        team_config=TeamConfig(teams=10, workday=Workday(start=time(8), end=time(17))),
        start_date=date(2025, 3, 3),  # Monday
        end_date=date(2025, 3, 5),    # Wednesday
        max_route_minutes=480,
        service_minutes_per_site=60,
        fast_mode=True,
    )

    result = plan_fixed_calendar(request)

    print("\n=== CALENDAR SMOKE TEST ===")
    print(f"Crews used: {result.crews_used}")
    print(f"Planning days used: {result.planning_days_used}")
    print(f"Team-days produced: {len(result.team_days)}")

    # ---- invariants ----

    # 1. All sites assigned
    assigned = [
        site_id
        for td in result.team_days
        for site_id in td.site_ids
    ]
    assert len(assigned) == len(sites), "Not all sites were assigned"

    # 2. No duplicate visits
    assert len(set(assigned)) == len(assigned), "Duplicate site visits detected"

    # 3. No unassigned
    assert result.unassigned == 0, "Unassigned sites remain"

    # 4. Dates are inside requested window
    for td in result.team_days:
        assert request.start_date <= td.date <= request.end_date

    print("Calendar smoke test PASSED")


if __name__ == "__main__":
    main()
