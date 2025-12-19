# src/scripts/test_solver_dual_mode_safe.py

from datetime import date, timedelta, time
from planning_engine.models import Site, PlanRequest, TeamConfig, Workday
from planning_engine.ortools_solver import plan_routes

def make_sites(num_sites: int):
    """Generate synthetic sites in a city grid for testing."""
    sites = []
    base_lat, base_lon = 38.6270, -90.1994  # example: St. Louis
    for i in range(num_sites):
        sites.append(Site(
            id=str(1000 + i),
            name=f"Site_{i}",
            lat=base_lat + (i * 0.001),
            lon=base_lon + (i * 0.001),
            service_minutes=60
        ))
    return sites

def print_team_days(result):
    for td in result.team_days:
        print(f"Team {td.team_id}: {len(td.site_ids)} sites, "
              f"service={td.service_minutes}, route={td.route_minutes}")
    print(f"Unassigned sites: {result.unassigned}")

def fixed_crews_test():
    """Fixed number of crews → show partial scheduling if needed."""
    sites = make_sites(50)  # tight schedule to force unassigned
    request = PlanRequest(
        workspace="test",
        sites=sites,
        team_config=TeamConfig(teams=3, workday=Workday(start=time(9,0), end=time(17,0))),
        num_crews_available=3,  # cap vehicles
        max_route_minutes=480
    )

    try:
        result = plan_routes(request)
    except RuntimeError:
        # Return empty plan if no solution, partial assignment will be reported in 'unassigned'
        result = type("EmptyResult", (), {})()
        result.team_days = []
        result.unassigned = len(sites)

    print("\n=== FIXED CREWS MODE ===")
    scheduled = sum(len(td.site_ids) for td in result.team_days)
    print(f"Scheduled {scheduled}/{len(sites)} sites")
    print_team_days(result)

def fixed_dates_test():
    """Fixed start/end date → solver chooses crews automatically."""
    sites = make_sites(50)
    start = date.today()
    end = start  # one day window to push solver
    request = PlanRequest(
        workspace="test",
        sites=sites,
        team_config=TeamConfig(teams=1, workday=Workday(start=time(9,0), end=time(17,0))),
        start_date=start,
        end_date=end,
        max_route_minutes=480,
        minimize_crews=True
    )

    result = plan_routes(request)

    print("\n=== FIXED DATES MODE ===")
    scheduled = sum(len(td.site_ids) for td in result.team_days)
    print(f"Scheduled {scheduled}/{len(sites)} sites")
    print(f"Used crews: {len(result.team_days)}")
    print_team_days(result)

def main():
    fixed_crews_test()
    fixed_dates_test()

if __name__ == "__main__":
    main()
