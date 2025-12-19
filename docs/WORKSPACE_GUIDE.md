# Workspace Management Guide

## Overview

The workspace management system allows you to organize multiple planning workflows in separate directories. Each workspace has its own folder structure for input data, output results, and cached data.

## Creating a Workspace

### Python API

```python
from planning_engine import new_workspace

# Create a new workspace
workspace_path = new_workspace("my_project_2025")
print(f"Workspace created at: {workspace_path}")
```

### FastAPI Endpoint

```bash
curl -X POST "http://localhost:8000/workspace" \
  -H "Content-Type: application/json" \
  -d '{"workspace_name": "my_project_2025"}'
```

Response:
```json
{
  "workspace_path": "data/workspace/my_project_2025",
  "message": "Workspace 'my_project_2025' created successfully"
}
```

## Workspace Structure

Each workspace has the following directory structure:

```
data/workspace/<workspace_name>/
├── input/    # Store input files (Excel, CSV, etc.)
├── output/   # Store planning results and reports
└── cache/    # Store cached data (geocoding results, distance matrices, etc.)
```

## Using Workspaces in Planning Requests

### Python API

```python
from datetime import time
from planning_engine import plan, new_workspace
from planning_engine.models import PlanRequest, Site, TeamConfig, Workday

# Create workspace
workspace_path = new_workspace("delivery_routes_jan_2025")

# Create planning request with workspace
request = PlanRequest(
    workspace="delivery_routes_jan_2025",  # Optional field
    sites=[
        Site(id="A", lat=38.6270, lon=-90.1994, service_minutes=30),
        Site(id="B", lat=38.6400, lon=-90.2500, service_minutes=45),
    ],
    team_config=TeamConfig(
        teams=1,
        workday=Workday(start=time(8, 0), end=time(17, 0))
    )
)

# Run planning
result = plan(request)
```

### FastAPI Endpoint

```bash
curl -X POST "http://localhost:8000/plan" \
  -H "Content-Type: application/json" \
  -d '{
    "workspace": "delivery_routes_jan_2025",
    "sites": [
      {"id": "A", "lat": 38.6270, "lon": -90.1994, "service_minutes": 30},
      {"id": "B", "lat": 38.6400, "lon": -90.2500, "service_minutes": 45}
    ],
    "team_config": {
      "teams": 1,
      "workday": {"start": "08:00:00", "end": "17:00:00"}
    }
  }'
```

## Workspace Name Rules

- Workspace names are automatically sanitized for security
- Only alphanumeric characters, hyphens, underscores, and spaces are allowed
- Path traversal attempts (e.g., `../../../etc/passwd`) are prevented
- Empty or invalid names will raise a `ValueError`

### Valid Examples
- `"my_project_2025"`
- `"Delivery Routes - January"`
- `"team_alpha_routes"`

### Invalid Examples
- `""` (empty string)
- `"   "` (only whitespace)
- `"///"` (only special characters)

## Best Practices

1. **Use descriptive names**: Choose workspace names that clearly identify the project or time period
2. **One workspace per project**: Keep different planning scenarios in separate workspaces
3. **Organize input files**: Place Excel files and other input data in the `input/` subdirectory
4. **Save results**: Write planning results to the `output/` subdirectory
5. **Cache reusable data**: Store geocoding results and distance matrices in `cache/` to avoid redundant API calls

## Example Workflow

```python
from planning_engine import new_workspace
from planning_engine.data_prep import parse_sites

# 1. Create workspace
workspace = new_workspace("q1_2025_routes")

# 2. Place your Excel file in the input directory
input_file = workspace / "input" / "sites.xlsx"
# (User manually copies file or you programmatically save it)

# 3. Parse the Excel file
sites = parse_sites(str(input_file))

# 4. Run planning with workspace context
request = PlanRequest(
    workspace="q1_2025_routes",
    sites=sites,
    team_config=team_config
)
result = plan(request)

# 5. Save results to output directory
output_file = workspace / "output" / "routes.json"
output_file.write_text(result.model_dump_json(indent=2))
```

## Testing

Run the workspace tests:

```bash
uv run pytest tests/test_workspace.py -v
```

See the example demo:

```bash
uv run python examples/workspace_demo.py
```
