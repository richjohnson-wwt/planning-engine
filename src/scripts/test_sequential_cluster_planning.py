"""Test sequential cluster planning with DC data."""

from datetime import date, time
from planning_engine import plan
from planning_engine.models import PlanRequest, TeamConfig, Workday


def test_sequential_cluster_planning():
    """
    Test that sequential cluster planning works with 3 crews and 4 clusters.
    
    Expected behavior:
    - All 19 sites should be planned (not just 17)
    - Crews work sequentially through clusters
    - When a crew finishes their cluster, they move to the next cluster
    """
    
    workspace_name = "pnc_phones"
    state_abbr = "DC"
    
    # Create request with 3 crews, fixed crew mode, clusters enabled
    request = PlanRequest(
        workspace=workspace_name,
        sites=[],  # Will be loaded from clustered.csv
        team_config=TeamConfig(
            teams=3,
            workday=Workday(start=time(8, 0), end=time(17, 0))
        ),
        state_abbr=state_abbr,
        use_clusters=True,
        start_date=date(2026, 3, 23),
        end_date=None,  # Fixed crew mode
        max_route_minutes=540,
        service_minutes_per_site=60,
        fast_mode=True
    )
    
    print("=" * 70)
    print("TESTING SEQUENTIAL CLUSTER PLANNING")
    print("=" * 70)
    print(f"\nWorkspace: {workspace_name}")
    print(f"State: {state_abbr}")
    print(f"Crews: {request.team_config.teams}")
    print(f"Mode: Fixed crew (sequential cluster planning)")
    print(f"Start date: {request.start_date}")
    
    # Run planning
    print("\n" + "=" * 70)
    result = plan(request)
    print("=" * 70)
    
    # Analyze results
    print("\n📊 RESULTS:")
    print(f"  • Total team-days: {len(result.team_days)}")
    print(f"  • Date range: {result.start_date} to {result.end_date}")
    print(f"  • Unassigned sites: {result.unassigned}")
    
    # Count unique sites
    all_site_ids = []
    for td in result.team_days:
        all_site_ids.extend(td.site_ids)
    unique_sites = set(all_site_ids)
    print(f"  • Unique sites planned: {len(unique_sites)}")
    
    # Count unique teams
    unique_teams = set(td.team_id for td in result.team_days)
    print(f"  • Unique teams used: {len(unique_teams)}")
    
    # Show schedule by date
    print("\n📅 SCHEDULE BY DATE:")
    dates = sorted(set(td.date for td in result.team_days if td.date))
    for d in dates:
        day_team_days = [td for td in result.team_days if td.date == d]
        total_sites_on_day = sum(len(td.site_ids) for td in day_team_days)
        teams_on_day = sorted(set(td.team_id for td in day_team_days))
        print(f"  {d}: {len(day_team_days)} team-days, {total_sites_on_day} sites, teams {teams_on_day}")
    
    # Show schedule by team
    print("\n👥 SCHEDULE BY TEAM:")
    for team_id in sorted(unique_teams):
        team_days = [td for td in result.team_days if td.team_id == team_id]
        total_sites = sum(len(td.site_ids) for td in team_days)
        dates_worked = sorted(set(td.date for td in team_days if td.date))
        print(f"  Team {team_id}: {len(team_days)} days, {total_sites} sites, dates {dates_worked}")
    
    # Verify expectations
    print("\n✅ VERIFICATION:")
    
    # Check 1: All sites should be planned
    expected_sites = 19
    if len(unique_sites) == expected_sites:
        print(f"  ✓ All {expected_sites} sites planned")
    else:
        print(f"  ✗ Only {len(unique_sites)}/{expected_sites} sites planned")
    
    # Check 2: Should use exactly 3 crews
    if len(unique_teams) == 3:
        print(f"  ✓ Exactly 3 crews used")
    else:
        print(f"  ✗ {len(unique_teams)} crews used (expected 3)")
    
    # Check 3: Should span multiple days
    if len(dates) > 1:
        print(f"  ✓ Multi-day scheduling ({len(dates)} days)")
    else:
        print(f"  ✗ Only 1 day used")
    
    # Check 4: No unassigned sites
    if result.unassigned == 0:
        print(f"  ✓ No unassigned sites")
    else:
        print(f"  ⚠️  {result.unassigned} unassigned sites")
    
    print("\n" + "=" * 70)
    
    # Final assessment
    if len(unique_sites) == expected_sites and len(unique_teams) == 3 and result.unassigned == 0:
        print("✅ SEQUENTIAL CLUSTER PLANNING TEST PASSED!")
        print("All sites planned with 3 crews working sequentially through clusters")
    else:
        print("⚠️  TEST RESULTS DIFFER FROM EXPECTED")
        print("This may indicate the sequential planning needs adjustment")
    
    print("=" * 70)


if __name__ == "__main__":
    test_sequential_cluster_planning()
