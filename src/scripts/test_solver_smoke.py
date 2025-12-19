# src/scripts/test_solver_smoke.py
from datetime import time
from planning_engine.models import Site, TeamConfig, Workday, PlanRequest
from planning_engine.ortools_solver import plan_single_day_vrp

def main():
    # --- 1. Small, deterministic dataset ---
    sites = [
        Site(id="6308", name="A", lat=38.6270, lon=-90.1994),
        Site(id="6309", name="B", lat=38.6400, lon=-90.2500),
        Site(id="6310", name="C", lat=38.6100, lon=-90.2100),
    ]

    # --- 2. Single crew, workday 9am-5pm ---
    team_config = TeamConfig(teams=1, workday=Workday(start=time(9,0), end=time(17,0)))

    # --- 3. Plan request ---
    request = PlanRequest(
        workspace="smoke_test_workspace",
        sites=sites,
        team_config=team_config,
        max_route_minutes=480,   # 8 hours, enough for 3 sites + travel
        service_minutes_per_site=60
    )

    # --- 4. Plan routes ---
    result = plan_single_day_vrp(request)

    # --- 5. Check for duplicates ---
    site_counts = {}
    for td in result.team_days:
        for sid in td.site_ids:
            site_counts[sid] = site_counts.get(sid, 0) + 1
    assert all(c == 1 for c in site_counts.values()), "Duplicate site visits detected"

    # --- 6. Check that all sites were assigned ---
    assigned_sites = set(site_counts.keys())
    expected_sites = set(s.id for s in sites)
    assert assigned_sites == expected_sites, "Not all sites were assigned"

    # --- 7. Print summary ---
    print("\n=== TEAM DAYS ===")
    for td in result.team_days:
        print(f"Team {td.team_id}: {len(td.site_ids)} sites, {td.route_minutes} min")
        print(f"   {td.site_ids}")

    print("\nSmoke test PASSED ✅")

if __name__ == "__main__":
    main()
