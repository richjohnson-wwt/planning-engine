from datetime import time
from planning_engine import plan
from planning_engine.models import PlanRequest, Site, TeamConfig, Workday, TeamDay, PlanResult

# Step 1: Create geocoded sites
sites = [
    Site(id="A", name="Site A", lat=38.6270, lon=-90.1994, service_minutes=30),
    Site(id="B", name="Site B", lat=38.6400, lon=-90.2500, service_minutes=45),
]

# Step 2: Define team configuration
team_config = TeamConfig(
    teams=1,
    workday=Workday(start=time(hour=8, minute=0), end=time(hour=17, minute=0))
)

# Step 3: Build the request
request = PlanRequest(
    workspace="example_workspace",
    sites=sites,
    team_config=team_config,
    fast_mode=True
)

# Step 4: Call the planning engine
result: PlanResult = plan(request)

# Step 5: Inspect result
for td in result.team_days:
    print(f"Team {td.team_id} will visit sites: {td.site_ids}, total minutes: {td.total_minutes}")
