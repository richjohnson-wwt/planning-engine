"""
Example: Fixed Crew Mode

This demonstrates planning with a fixed number of crews where the system
calculates how many days are needed to complete all sites.

User provides:
- start_date: When to begin work
- team_config.teams: Number of crews available

System calculates:
- end_date: When all sites will be completed
"""

from datetime import date, time
from planning_engine.api import plan
from planning_engine.models import PlanRequest, Site, TeamConfig, Workday

# Create sample sites
sites = [
    Site(id=f"Site_{i}", name=f"Site {i}", lat=38.6 + i*0.01, lon=-90.2 + i*0.01, service_minutes=60)
    for i in range(20)  # 20 sites to schedule
]

# Configure team with 2 crews
team_config = TeamConfig(
    teams=2,  # Fixed: only 2 crews available
    workday=Workday(start=time(9, 0), end=time(17, 0))
)

# Create request for FIXED CREW mode
# Note: Only start_date is provided, NOT end_date
request = PlanRequest(
    workspace="fixed_crew_demo",
    sites=sites,
    team_config=team_config,
    start_date=date(2025, 1, 6),  # Monday - when to start
    # end_date is NOT provided - system will calculate it!
    max_route_minutes=480,  # 8 hours
    service_minutes_per_site=60,
    fast_mode=True
)

print("Planning with Fixed Crew Mode...")
print(f"Start Date: {request.start_date}")
print(f"Number of Crews: {team_config.teams}")
print(f"Number of Sites: {len(sites)}")
print()

# Run planning
result = plan(request)

# Display results
print("="*60)
print("RESULTS")
print("="*60)
print(f"Start Date: {result.start_date}")
print(f"End Date: {result.end_date} (CALCULATED)")
print(f"Total Sites Scheduled: {len(sites) - result.unassigned}/{len(sites)}")
print(f"Total Team-Days: {len(result.team_days)}")
print()

# Show schedule by date
from collections import defaultdict
schedule_by_date = defaultdict(list)
for td in result.team_days:
    if td.date:
        schedule_by_date[td.date].append(td)

for day in sorted(schedule_by_date.keys()):
    print(f"\n{day} ({day.strftime('%A')}):")
    for td in schedule_by_date[day]:
        print(f"  Crew {td.team_id}: {len(td.site_ids)} sites, {td.route_minutes} minutes")

print(f"\n{'='*60}")
print(f"Project Duration: {(result.end_date - result.start_date).days + 1} days")
print(f"{'='*60}")
