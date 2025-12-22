from datetime import time, date
from planning_engine import plan
from planning_engine.models import PlanRequest, Site, TeamConfig, Workday, PlanResult

# Example: Using OR-Tools solver for optimized multi-day, multi-crew routing

# Step 1: Create geocoded sites (more sites for realistic routing)
sites = [
    Site(id="A", name="Site A", lat=38.6270, lon=-90.1994, service_minutes=60),
    Site(id="B", name="Site B", lat=38.6400, lon=-90.2500, service_minutes=60),
    Site(id="C", name="Site C", lat=38.6500, lon=-90.2000, service_minutes=60),
    Site(id="D", name="Site D", lat=38.6350, lon=-90.2200, service_minutes=60),
    Site(id="E", name="Site E", lat=38.6450, lon=-90.1900, service_minutes=60),
]

# Step 2: Define team configuration
team_config = TeamConfig(
    teams=2,  # 2 crews available
    workday=Workday(start=time(hour=8, minute=0), end=time(hour=17, minute=0))
)

# Step 3: Build the request with OR-Tools specific fields
request = PlanRequest(
    workspace="example_workspace",
    sites=sites,
    state_abbr='LA',
    team_config=team_config,
    # OR-Tools specific fields
    start_date=date(2025, 1, 6),  # Monday
    end_date=date(2025, 1, 8),    # Wednesday (3 days)

    max_route_minutes=480,  # 8 hours
    break_minutes=30,
    holidays=[],  # No holidays in this period
    fast_mode=True
)

# Step 4: Call the planning engine (will use OR-Tools solver)
print("Running OR-Tools solver for optimized routing...")
result: PlanResult = plan(request)

# Step 5: Display results
print(f"\n{'='*60}")
print("OPTIMIZED ROUTE PLAN")
print(f"{'='*60}\n")

# Display date range
if result.start_date:
    print(f"Start Date: {result.start_date}")
if result.end_date:
    print(f"End Date: {result.end_date}")
if result.start_date or result.end_date:
    print()

# Group by team
team_schedule = {}
for td in result.team_days:
    if td.team_id not in team_schedule:
        team_schedule[td.team_id] = []
    team_schedule[td.team_id].append(td)

for team_id in sorted(team_schedule.keys()):
    print(f"Team/Crew {team_id}:")
    for idx, td in enumerate(team_schedule[team_id], 1):
        site_names = [s.name for s in sites if s.id in td.site_ids]
        print(f"  Day {idx}: {', '.join(site_names)} ({td.route_minutes} minutes)")
    print()

# Summary
total_sites = len(set(site_id for td in result.team_days for site_id in td.site_ids))
print(f"Total sites scheduled: {total_sites}/{len(sites)}")
print(f"Total team-days used: {len(result.team_days)}")
