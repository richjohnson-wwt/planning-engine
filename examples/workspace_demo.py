"""
Demo script showing how to use the workspace management system.
"""
from datetime import time
from planning_engine import plan, new_workspace
from planning_engine.models import PlanRequest, Site, TeamConfig, Workday

# Step 1: Create a new workspace
print("Creating workspace...")
workspace_path = new_workspace("my_project_2025")
print(f"✓ Workspace created at: {workspace_path}")
print(f"  - Input folder: {workspace_path / 'input'}")
print(f"  - Output folder: {workspace_path / 'output'}")
print(f"  - Cache folder: {workspace_path / 'cache'}")

# Step 2: Create sites
sites = [
    Site(id="A", lat=38.6270, lon=-90.1994, service_minutes=30),
    Site(id="B", lat=38.6400, lon=-90.2500, service_minutes=45),
    Site(id="C", lat=38.6100, lon=-90.2100, service_minutes=20),
]

# Step 3: Define team configuration
team_config = TeamConfig(
    teams=1,
    workday=Workday(start=time(hour=8, minute=0), end=time(hour=17, minute=0))
)

# Step 4: Build the request with workspace
request = PlanRequest(
    workspace="my_project_2025",
    sites=sites,
    team_config=team_config
)

# Step 5: Call the planning engine
print("\nRunning planning engine...")
result = plan(request)

# Step 6: Display results
print("\n✓ Planning complete!")
for td in result.team_days:
    print(f"  Team {td.team_id}: visits {td.site_ids}, total time: {td.total_minutes} minutes")
