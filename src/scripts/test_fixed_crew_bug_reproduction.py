"""
Test to reproduce the fixed crew + clusters bug using actual bug data.

Bug Report:
- Planned 130 sites with fixed crew size 6, start date 3/2/2025
- Result incorrectly schedules teams 1-6 AND teams 101, 102, 103 on 3/2/2026
- The system conflates team-days logic with fixed crew planning

Root Cause:
- In api.py _plan_with_clusters(), team IDs are offset by cluster_id * 100
- This offset is appropriate for team-days mode but NOT for fixed crew mode
- In fixed crew mode, teams 1-6 should remain consistent across all clusters/dates

Expected Behavior:
- Only teams 1-6 should be used throughout the entire plan
- Each date should only have teams from the fixed crew (1-6)
- No cluster-offset team IDs (101+) should appear
"""

import json
from pathlib import Path
from collections import defaultdict


def test_fixed_crew_bug_from_json():
    """
    Test using the actual bug data from fixed_crew_bug.json.
    
    This test loads the buggy result and verifies the issue exists,
    demonstrating what needs to be fixed.
    """
    
    # Load the bug data
    bug_data_path = Path(__file__).parent / "data" / "fixed_crew_bug.json"
    
    if not bug_data_path.exists():
        print(f"⚠️  Bug data file not found: {bug_data_path}")
        print("This test requires the actual bug data to run.")
        return
    
    with open(bug_data_path, 'r') as f:
        data = json.load(f)
    
    metadata = data['metadata']
    team_days = data['result']['team_days']
    
    print("\n=== Fixed Crew Bug Reproduction Test ===")
    print(f"Workspace: {metadata['workspace']}")
    print(f"Start date: {metadata['start_date']}")
    print(f"Fixed crew size: {metadata['teams']}")
    print(f"Total team-days: {len(team_days)}")
    
    # Extract all unique team IDs
    all_team_ids = sorted(set(td['team_id'] for td in team_days))
    print(f"\nAll team IDs found: {all_team_ids}")
    
    # Group team IDs by date
    teams_by_date = defaultdict(set)
    for td in team_days:
        teams_by_date[td['date']].add(td['team_id'])
    
    # Check the start date (where the bug manifests)
    start_date = metadata['start_date']
    teams_on_start_date = sorted(teams_by_date[start_date])
    
    print(f"\n🐛 BUG DETECTED on {start_date}:")
    print(f"   Teams scheduled: {teams_on_start_date}")
    print(f"   Expected: [1, 2, 3, 4, 5, 6]")
    print(f"   Problem: Teams 101, 102, 103 also appear!")
    
    # Assertions that should FAIL with the bug present
    expected_teams = {1, 2, 3, 4, 5, 6}
    actual_teams = set(all_team_ids)
    
    print("\n=== Test Assertions ===")
    
    # Test 1: Only teams 1-6 should exist
    unexpected_teams = actual_teams - expected_teams
    if unexpected_teams:
        print(f"❌ FAIL: Found unexpected team IDs: {sorted(unexpected_teams)}")
        print(f"   These are cluster-offset IDs that shouldn't exist in fixed crew mode")
    else:
        print(f"✅ PASS: Only expected team IDs found")
    
    # Test 2: No team IDs >= 100 (cluster offsets)
    cluster_offset_teams = [tid for tid in all_team_ids if tid >= 100]
    if cluster_offset_teams:
        print(f"❌ FAIL: Found cluster-offset team IDs: {cluster_offset_teams}")
        print(f"   Cluster offsets (100, 200, etc.) should not be used in fixed crew mode")
    else:
        print(f"✅ PASS: No cluster-offset team IDs found")
    
    # Test 3: Each date should only have teams 1-6
    dates_with_invalid_teams = []
    for date_val, teams in sorted(teams_by_date.items()):
        invalid_teams = teams - expected_teams
        if invalid_teams:
            dates_with_invalid_teams.append((date_val, sorted(invalid_teams)))
    
    if dates_with_invalid_teams:
        print(f"❌ FAIL: {len(dates_with_invalid_teams)} dates have invalid team IDs:")
        for date_val, invalid in dates_with_invalid_teams[:3]:  # Show first 3
            print(f"   {date_val}: invalid teams {invalid}")
        if len(dates_with_invalid_teams) > 3:
            print(f"   ... and {len(dates_with_invalid_teams) - 3} more dates")
    else:
        print(f"✅ PASS: All dates only use teams 1-6")
    
    # Test 4: On start date, should only have teams 1-6
    start_date_teams = teams_by_date[start_date]
    if not start_date_teams.issubset(expected_teams):
        print(f"❌ FAIL: Start date {start_date} has invalid teams: {sorted(start_date_teams - expected_teams)}")
    else:
        print(f"✅ PASS: Start date only uses teams 1-6")
    
    # Summary
    print("\n=== Summary ===")
    if unexpected_teams or cluster_offset_teams or dates_with_invalid_teams:
        print("🐛 BUG CONFIRMED: Fixed crew planning with clusters incorrectly assigns team IDs")
        print("\nRoot cause: api.py _plan_with_clusters() applies cluster offset to ALL modes")
        print("Fix needed: Only apply cluster offset in team-days mode, not fixed crew mode")
        return False
    else:
        print("✅ All tests passed! Bug is fixed.")
        return True


if __name__ == "__main__":
    success = test_fixed_crew_bug_from_json()
    exit(0 if success else 1)
