"""
Test to reproduce the duplicate team ID bug reported by user.

User's scenario:
- Fixed calendar planning (start: 3/9/26, end: 4/6/26)
- 2 teams specified (but system calculates actual crews needed)
- Use clusters: True
- Result shows Team 1 scheduled twice on same date (3/9/26)

Expected: Each team-day should have a unique team ID
Actual (buggy): Team 1 appears twice on 3/9/26
"""

from datetime import date, time
from pathlib import Path
import json


def test_duplicate_team_id_from_user_data():
    """
    Test using the actual user's bug data from fixed_calendar_IL_jitb.json.
    """
    
    # Load the user's bug data
    bug_data_path = Path(__file__).parent / "data" / "fixed_calendar_IL_jitb.json"
    
    if not bug_data_path.exists():
        print(f"⚠️  Bug data file not found: {bug_data_path}")
        print("This test requires the actual bug data to run.")
        return
    
    with open(bug_data_path, 'r') as f:
        data = json.load(f)
    
    team_days = data['result']['team_days']
    
    print("\n=== Duplicate Team ID Bug Test ===")
    print(f"Total team-days: {len(team_days)}")
    
    # Group by date and check for duplicate team IDs
    from collections import defaultdict
    teams_by_date = defaultdict(list)
    
    for td in team_days:
        teams_by_date[td['date']].append({
            'team_id': td['team_id'],
            'num_sites': len(td['site_ids']),
            'first_site': td['site_ids'][0] if td['site_ids'] else None
        })
    
    print("\n=== Team Schedule ===")
    has_duplicates = False
    
    for date_val in sorted(teams_by_date.keys()):
        teams = teams_by_date[date_val]
        print(f"\n{date_val}:")
        
        team_ids_on_date = []
        for team in teams:
            print(f"  Team {team['team_id']}: {team['num_sites']} sites (first: {team['first_site']})")
            team_ids_on_date.append(team['team_id'])
        
        # Check for duplicates on this date
        if len(team_ids_on_date) != len(set(team_ids_on_date)):
            duplicates = [tid for tid in set(team_ids_on_date) if team_ids_on_date.count(tid) > 1]
            print(f"  ❌ DUPLICATE TEAM IDs: {duplicates}")
            has_duplicates = True
    
    print("\n=== Test Result ===")
    if has_duplicates:
        print("❌ FAIL: Found duplicate team IDs on the same date")
        print("This is the bug - each team-day should have a unique team ID")
        return False
    else:
        print("✅ PASS: No duplicate team IDs on any date")
        return True


if __name__ == "__main__":
    success = test_duplicate_team_id_from_user_data()
    exit(0 if success else 1)
