"""
Integration test to verify the fixed crew + clusters bug is fixed.

This test creates a minimal workspace with clustered sites and runs
the actual planning code to verify team IDs are correct.
"""

from datetime import date, time
from pathlib import Path
import tempfile
import shutil
import pandas as pd

from planning_engine.api import plan, new_workspace, cluster
from planning_engine.models import PlanRequest, TeamConfig, Workday
from planning_engine.paths import get_workspace_path


def test_fixed_crew_with_clusters_integration():
    """
    Integration test: Create workspace, cluster sites, and plan with fixed crews.
    Verify that team IDs remain consistent (1-N) across all clusters.
    """
    
    # Create a temporary workspace
    workspace_name = "test_cluster_fix"
    
    try:
        # Clean up if it exists
        workspace_path = get_workspace_path(workspace_name)
        if workspace_path.exists():
            shutil.rmtree(workspace_path)
        
        # Create new workspace
        new_workspace(workspace_name)
        
        # Create test data with sites in two geographic clusters
        # Cluster 1: Chicago area (lat ~41.8, lon ~-87.9)
        # Cluster 2: Bloomington area (lat ~40.5, lon ~-88.9)
        sites_data = []
        
        # Chicago cluster (30 sites)
        for i in range(30):
            sites_data.append({
                'site_id': f'CHI-{i}',
                'street1': f'{100 + i} N Michigan Ave',
                'city': 'Chicago',
                'state': 'IL',
                'zip': '60601',
                'lat': 41.8 + i * 0.01,
                'lon': -87.9 + i * 0.01,
            })
        
        # Bloomington cluster (30 sites)
        for i in range(30):
            sites_data.append({
                'site_id': f'BLM-{i}',
                'street1': f'{200 + i} E Washington St',
                'city': 'Bloomington',
                'state': 'IL',
                'zip': '61701',
                'lat': 40.5 + i * 0.01,
                'lon': -88.9 + i * 0.01,
            })
        
        # Save geocoded.csv
        df = pd.DataFrame(sites_data)
        state_cache_dir = workspace_path / "cache" / "IL"
        state_cache_dir.mkdir(parents=True, exist_ok=True)
        geocoded_path = state_cache_dir / "geocoded.csv"
        df.to_csv(geocoded_path, index=False)
        print(f"✓ Created geocoded.csv with {len(df)} sites")
        
        # Run clustering
        cluster(workspace_name, state_abbr="IL")
        
        # Verify clustered.csv was created
        clustered_path = state_cache_dir / "clustered.csv"
        assert clustered_path.exists(), "clustered.csv not created"
        
        clustered_df = pd.read_csv(clustered_path)
        num_clusters = clustered_df['cluster_id'].nunique()
        print(f"✓ Created {num_clusters} clusters")
        
        # Now run planning with fixed crew and clusters
        request = PlanRequest(
            workspace=workspace_name,
            sites=[],  # Will be loaded from clustered.csv
            team_config=TeamConfig(
                teams=6,
                workday=Workday(start=time(8, 0), end=time(17, 0))
            ),
            state_abbr="IL",
            use_clusters=True,
            start_date=date(2026, 3, 2),
            max_route_minutes=480,
            service_minutes_per_site=60,
            fast_mode=True
        )
        
        print(f"\n=== Running Fixed Crew Planning with Clusters ===")
        print(f"Fixed crew size: {request.team_config.teams}")
        print(f"Start date: {request.start_date}")
        print(f"Using clusters: {request.use_clusters}")
        
        result = plan(request)
        
        print(f"\n=== Results ===")
        print(f"Total team-days: {len(result.team_days)}")
        print(f"Date range: {result.start_date} to {result.end_date}")
        
        # Extract all unique team IDs
        all_team_ids = sorted(set(td.team_id for td in result.team_days))
        print(f"Team IDs found: {all_team_ids}")
        
        # ASSERTIONS
        print(f"\n=== Test Assertions ===")
        
        # Test 1: Only teams 1-6 should exist
        expected_teams = {1, 2, 3, 4, 5, 6}
        actual_teams = set(all_team_ids)
        unexpected_teams = actual_teams - expected_teams
        
        assert not unexpected_teams, \
            f"❌ FAIL: Found unexpected team IDs: {sorted(unexpected_teams)}"
        print(f"✅ PASS: Only expected team IDs found (1-6)")
        
        # Test 2: No team IDs >= 100 (cluster offsets)
        cluster_offset_teams = [tid for tid in all_team_ids if tid >= 100]
        assert not cluster_offset_teams, \
            f"❌ FAIL: Found cluster-offset team IDs: {cluster_offset_teams}"
        print(f"✅ PASS: No cluster-offset team IDs found")
        
        # Test 3: Each date should only have teams 1-6
        from collections import defaultdict
        teams_by_date = defaultdict(set)
        for td in result.team_days:
            teams_by_date[td.date].add(td.team_id)
        
        for date_val, teams in sorted(teams_by_date.items()):
            invalid_teams = teams - expected_teams
            assert not invalid_teams, \
                f"❌ FAIL: Date {date_val} has invalid team IDs: {sorted(invalid_teams)}"
        print(f"✅ PASS: All {len(teams_by_date)} dates only use teams 1-6")
        
        # Test 4: Start date should only have teams 1-6
        start_date_teams = teams_by_date[request.start_date]
        assert start_date_teams.issubset(expected_teams), \
            f"❌ FAIL: Start date has invalid teams: {sorted(start_date_teams - expected_teams)}"
        print(f"✅ PASS: Start date only uses teams 1-6")
        
        print(f"\n🎉 All tests passed! Bug is fixed.")
        return True
        
    finally:
        # Clean up
        workspace_path = get_workspace_path(workspace_name)
        if workspace_path.exists():
            shutil.rmtree(workspace_path)
            print(f"\n✓ Cleaned up test workspace")


if __name__ == "__main__":
    try:
        success = test_fixed_crew_with_clusters_integration()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
