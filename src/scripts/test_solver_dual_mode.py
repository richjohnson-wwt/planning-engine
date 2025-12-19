# src/scripts/test_solver_dual_mode_safe.py

from datetime import date, timedelta, time
from planning_engine.models import Site, PlanRequest, TeamConfig, Workday
from planning_engine.ortools_solver import plan_single_day_vrp

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
    """Fixed number of crews → show single-day capacity with crew constraint."""
    sites = make_sites(50)
    
    # Single-day optimization: What can 3 crews accomplish in 1 day?
    request = PlanRequest(
        workspace="test",
        sites=sites,
        team_config=TeamConfig(teams=3, workday=Workday(start=time(9,0), end=time(17,0))),
        num_crews_available=3,  # Fixed: only 3 crews available
        max_route_minutes=480,
        minimize_crews=False  # Use all available crews
    )

    result = plan_single_day_vrp(request)

    print("\n=== FIXED CREWS MODE (Single-Day VRP) ===")
    scheduled = sum(len(td.site_ids) for td in result.team_days)
    print(f"Scheduled {scheduled}/{len(sites)} sites in 1 day with 3 crews")
    
    # Calculate how many days would be needed to complete all sites
    if scheduled > 0:
        days_needed = (len(sites) + scheduled - 1) // scheduled  # Ceiling division
        print(f"Estimated days to complete all {len(sites)} sites: ~{days_needed} days")
    
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

    result = plan_single_day_vrp(request)

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
