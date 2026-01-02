"""
Test to verify that fixed calendar planning with clusters assigns sequential team IDs.

When using fixed calendar mode (start_date + end_date specified), the system calculates
how many crews are needed. With clusters, each cluster is planned independently, which
previously resulted in duplicate team IDs (e.g., cluster 0: teams 1-3, cluster 1: teams 1-3).

This test verifies that team IDs are renumbered sequentially (1, 2, 3, 4, 5, 6...) across
all clusters, not offset by 100s or duplicated.
"""

from datetime import date, time
from pathlib import Path
import tempfile
import shutil
import pandas as pd

from planning_engine.api import plan, new_workspace, cluster
from planning_engine.models import PlanRequest, TeamConfig, Workday
from planning_engine.paths import get_workspace_path


def test_fixed_calendar_with_clusters_sequential_teams():
    """
    Test that fixed calendar planning with clusters assigns sequential team IDs.
    """
    
    # Create a temporary workspace
    workspace_name = "test_fixed_calendar_teams"
    
    try:
        # Clean up if it exists
        workspace_path = get_workspace_path(workspace_name)
        if workspace_path.exists():
            shutil.rmtree(workspace_path)
        
        # Create new workspace
        new_workspace(workspace_name)
        
        # Create test data with sites in two geographic clusters
        # Each cluster should need ~2-3 crews to complete in one day
        sites_data = []
        
        # Cluster 1: Chicago area (40 sites - needs multiple crews)
        for i in range(40):
            sites_data.append({
                'site_id': f'CHI-{i}',
                'street1': f'{100 + i} N Michigan Ave',
                'city': 'Chicago',
                'state': 'IL',
                'zip': '60601',
                'lat': 41.8 + i * 0.01,
                'lon': -87.9 + i * 0.01,
            })
        
        # Cluster 2: Bloomington area (40 sites - needs multiple crews)
        for i in range(40):
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
        
        # Now run FIXED CALENDAR planning (system calculates crews needed)
        request = PlanRequest(
            workspace=workspace_name,
            sites=[],  # Will be loaded from clustered.csv
            team_config=TeamConfig(
                teams=1,  # This will be ignored - system calculates crews needed
                workday=Workday(start=time(8, 0), end=time(17, 0))
            ),
            state_abbr="IL",
            use_clusters=True,
            start_date=date(2026, 3, 2),
            end_date=date(2026, 3, 2),  # Single day - forces multiple crews
            max_route_minutes=480,
            service_minutes_per_site=60,
            fast_mode=True
        )
        
        print(f"\n=== Running Fixed Calendar Planning with Clusters ===")
        print(f"Date range: {request.start_date} to {request.end_date}")
        print(f"Using clusters: {request.use_clusters}")
        print(f"System will calculate crews needed...")
        
        result = plan(request)
        
        print(f"\n=== Results ===")
        print(f"Total team-days: {len(result.team_days)}")
        print(f"Date range: {result.start_date} to {result.end_date}")
        
        # Extract all unique team IDs
        all_team_ids = sorted(set(td.team_id for td in result.team_days))
        print(f"Team IDs found: {all_team_ids}")
        
        # ASSERTIONS
        print(f"\n=== Test Assertions ===")
        
        # Test 1: Team IDs should be sequential starting from 1
        expected_teams = set(range(1, len(all_team_ids) + 1))
        actual_teams = set(all_team_ids)
        
        assert actual_teams == expected_teams, \
            f"❌ FAIL: Team IDs not sequential. Expected {sorted(expected_teams)}, got {all_team_ids}"
        print(f"✅ PASS: Team IDs are sequential (1-{len(all_team_ids)})")
        
        # Test 2: No cluster-offset team IDs (>= 100)
        cluster_offset_teams = [tid for tid in all_team_ids if tid >= 100]
        assert not cluster_offset_teams, \
            f"❌ FAIL: Found cluster-offset team IDs: {cluster_offset_teams}"
        print(f"✅ PASS: No cluster-offset team IDs found")
        
        # Test 3: No gaps in team ID sequence
        for i in range(1, len(all_team_ids)):
            assert all_team_ids[i] == all_team_ids[i-1] + 1, \
                f"❌ FAIL: Gap in team ID sequence between {all_team_ids[i-1]} and {all_team_ids[i]}"
        print(f"✅ PASS: No gaps in team ID sequence")
        
        # Test 4: Multiple teams were calculated (not just 1)
        assert len(all_team_ids) > 1, \
            f"❌ FAIL: Only {len(all_team_ids)} team(s) calculated, expected multiple"
        print(f"✅ PASS: System calculated {len(all_team_ids)} crews needed")
        
        # Test 5: All team IDs on a given date should be unique
        from collections import defaultdict
        teams_by_date = defaultdict(set)
        for td in result.team_days:
            teams_by_date[td.date].add(td.team_id)
        
        for date_val, teams in teams_by_date.items():
            team_list = sorted(teams)
            assert len(team_list) == len(set(team_list)), \
                f"❌ FAIL: Duplicate team IDs on {date_val}: {team_list}"
        print(f"✅ PASS: No duplicate team IDs on any date")
        
        print(f"\n🎉 All tests passed! Team IDs are sequential: {all_team_ids}")
        return True
        
    finally:
        # Clean up
        workspace_path = get_workspace_path(workspace_name)
        if workspace_path.exists():
            shutil.rmtree(workspace_path)
            print(f"\n✓ Cleaned up test workspace")


if __name__ == "__main__":
    try:
        success = test_fixed_calendar_with_clusters_sequential_teams()
        exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
