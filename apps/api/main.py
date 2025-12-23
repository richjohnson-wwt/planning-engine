from fastapi import FastAPI, UploadFile, File, Form
from planning_engine import plan, new_workspace, parse_excel, geocode, cluster
from planning_engine.models import PlanRequest, PlanResult
from planning_engine.paths import get_project_root
from pydantic import BaseModel
from pathlib import Path
import warnings
import logging
import json
import tempfile

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Suppress Pydantic serialization warnings for optional date fields
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic.type_adapter")

app = FastAPI(title="Planning Engine API")


class WorkspaceRequest(BaseModel):
    workspace_name: str


class WorkspaceResponse(BaseModel):
    workspace_path: str
    message: str


class ParseExcelRequest(BaseModel):
    workspace_name: str
    file_path: str
    sheet_name: str = ""  # Optional: if empty, uses first sheet
    column_mapping: dict[str, str]
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "workspace_name": "my_project_2025",
                    "file_path": "/Users/johnsori/Downloads/AscensionClean.xlsx",
                    "sheet_name": "workstations",
                    "column_mapping": {
                        "site_id": "Lab name",
                        "street1": "Address (Location)",
                        "city": "City",
                        "state": "State",
                        "zip": "Zip Code"
                    }
                }
            ]
        }
    }


class ParseExcelResponse(BaseModel):
    output_path: str
    message: str


class GeocodeRequest(BaseModel):
    workspace_name: str
    state_abbr: str
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "workspace_name": "my_project_2025",
                    "state_abbr": "LA"
                }
            ]
        }
    }


class GeocodeResponse(BaseModel):
    output_path: str
    message: str
    addresses_geocoded: int


class ClusterRequest(BaseModel):
    workspace_name: str
    state_abbr: str
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "workspace_name": "my_project_2025",
                    "state_abbr": "LA"
                }
            ]
        }
    }


class ClusterResponse(BaseModel):
    output_path: str
    message: str
    sites_clustered: int
    num_clusters: int


@app.get("/workspaces")
def list_workspaces():
    """List all existing workspaces"""
    workspace_dir = get_project_root() / "data" / "workspace"
    if not workspace_dir.exists():
        return {"workspaces": []}
    
    # Get all subdirectories in data/workspace
    workspaces = [
        d.name for d in workspace_dir.iterdir() 
        if d.is_dir() and not d.name.startswith('.')
    ]
    
    return {"workspaces": sorted(workspaces)}


@app.get("/workspaces/{workspace_name}/states")
def list_workspace_states(workspace_name: str):
    """List all state subdirectories with detailed information (site count, geocode status)"""
    import pandas as pd
    
    workspace_path = get_project_root() / "data" / "workspace" / workspace_name
    input_dir = workspace_path / "input"
    cache_dir = workspace_path / "cache"
    
    if not input_dir.exists():
        return {"states": []}
    
    # Get all subdirectories in the input folder
    state_dirs = [
        d for d in input_dir.iterdir() 
        if d.is_dir() and not d.name.startswith('.')
    ]
    
    states_info = []
    for state_dir in sorted(state_dirs, key=lambda d: d.name):
        state_name = state_dir.name
        addresses_csv = state_dir / "addresses.csv"
        geocoded_csv = cache_dir / state_name / "geocoded.csv"
        
        # Count sites from addresses.csv
        site_count = 0
        if addresses_csv.exists():
            try:
                df = pd.read_csv(addresses_csv)
                site_count = len(df)
            except Exception:
                site_count = 0
        
        # Check if geocoded
        geocoded = geocoded_csv.exists()
        
        states_info.append({
            "name": state_name,
            "site_count": site_count,
            "geocoded": geocoded
        })
    
    return {"states": states_info}


@app.post("/workspace", response_model=WorkspaceResponse)
def create_workspace(request: WorkspaceRequest):
    """Create a new workspace for organizing planning workflows"""
    workspace_path = new_workspace(request.workspace_name)
    return WorkspaceResponse(
        workspace_path=str(workspace_path),
        message=f"Workspace '{request.workspace_name}' created successfully"
    )


@app.post("/parse-excel", response_model=ParseExcelResponse)
def parse_excel_file(request: ParseExcelRequest):
    """Parse an Excel file and map columns to standard fields, organized by state"""
    state_files = parse_excel(
        workspace_name=request.workspace_name,
        file_path=request.file_path,
        sheet_name=request.sheet_name if request.sheet_name else None,
        column_mapping=request.column_mapping
    )
    
    # Create summary message
    states_list = ', '.join(state_files.keys())
    first_state_path = str(next(iter(state_files.values())))
    
    return ParseExcelResponse(
        output_path=first_state_path,  # Return first state's path for backward compatibility
        message=f"Excel file parsed successfully. Sites organized by state: {states_list}. "
                f"Files saved to data/workspace/{request.workspace_name}/input/{{STATE}}/addresses.csv"
    )


@app.post("/parse-excel-upload", response_model=ParseExcelResponse)
async def parse_excel_upload(
    file: UploadFile = File(...),
    workspace_name: str = Form(...),
    sheet_name: str = Form(""),
    column_mapping: str = Form(...)
):
    """Parse an uploaded Excel file and map columns to standard fields, organized by state"""
    # Parse the JSON column mapping
    column_mapping_dict = json.loads(column_mapping)
    
    # Save uploaded file to a temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
        content = await file.read()
        tmp_file.write(content)
        tmp_file_path = tmp_file.name
    
    try:
        # Parse the Excel file
        state_files = parse_excel(
            workspace_name=workspace_name,
            file_path=tmp_file_path,
            sheet_name=sheet_name if sheet_name else None,
            column_mapping=column_mapping_dict
        )
        
        # Create summary message
        states_list = ', '.join(state_files.keys())
        first_state_path = str(next(iter(state_files.values())))
        
        return ParseExcelResponse(
            output_path=first_state_path,
            message=f"Excel file '{file.filename}' parsed successfully. Sites organized by state: {states_list}. "
                    f"Files saved to data/workspace/{workspace_name}/input/{{STATE}}/addresses.csv"
        )
    finally:
        # Clean up temporary file
        import os
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)


@app.post("/geocode", response_model=GeocodeResponse)
def geocode_addresses(request: GeocodeRequest):
    """Geocode addresses from workspace's state-specific addresses.csv file"""
    import pandas as pd
    output_path = geocode(workspace_name=request.workspace_name, state_abbr=request.state_abbr)
    
    # Count how many addresses were geocoded
    df = pd.read_csv(output_path)
    addresses_count = len(df)
    
    return GeocodeResponse(
        output_path=str(output_path),
        message=f"Geocoding completed for state '{request.state_abbr}'. Results saved to {output_path}",
        addresses_geocoded=addresses_count
    )


@app.post("/cluster", response_model=ClusterResponse)
def cluster_sites(request: ClusterRequest):
    """Cluster geocoded sites based on geographic coordinates"""
    import pandas as pd
    output_path = cluster(workspace_name=request.workspace_name, state_abbr=request.state_abbr)
    
    # Get cluster statistics
    df = pd.read_csv(output_path)
    sites_count = len(df)
    num_clusters = len(df[df['cluster_id'] >= 0]['cluster_id'].unique())
    
    return ClusterResponse(
        output_path=str(output_path),
        message=f"Clustering completed for state '{request.state_abbr}'. {sites_count} sites assigned to {num_clusters} clusters",
        sites_clustered=sites_count,
        num_clusters=num_clusters
    )


@app.post("/plan", response_model=PlanResult)
def run_plan(request: PlanRequest):
    """
    Plan routes for teams/crews to visit sites.
    
    Results are automatically saved to the workspace output folder organized by state:
    - data/workspace/{workspace}/output/{STATE}/route_plan_{timestamp}.json
    
    JSON includes metadata wrapper with request parameters and planning results.
    """
    from pathlib import Path
    import json
    from datetime import datetime
    import logging
    
    logger = logging.getLogger(__name__)
    
    # Log the incoming request
    logger.info("=" * 80)
    logger.info("PLANNING REQUEST RECEIVED")
    logger.info(f"Workspace: {request.workspace}")
    logger.info(f"State: {request.state_abbr}")
    logger.info(f"Teams: {request.team_config.teams}")
    logger.info(f"Start Date: {request.start_date}")
    logger.info(f"End Date: {request.end_date or 'Auto-calculate (Fixed Crew Mode)'}")
    logger.info(f"Use Clusters: {request.use_clusters}")
    logger.info(f"Max Route Minutes: {request.max_route_minutes}")
    logger.info(f"Service Minutes/Site: {request.service_minutes_per_site}")
    logger.info(f"Fast Mode: {request.fast_mode}")
    logger.info("=" * 80)
    
    # Run the planning
    logger.info("Starting route planning...")
    result = plan(request)
    logger.info(f"Planning completed! Total routes: {len(result.team_days)}")
    
    # Save results to workspace output folder organized by state
    if request.workspace and request.state_abbr:
        # Create state-specific output directory (matching cache structure)
        output_dir = get_project_root() / "data" / "workspace" / request.workspace / "output" / request.state_abbr
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Add timestamp to filename for versioning
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Build metadata wrapper with request parameters
        output_data = {
            "metadata": {
                "workspace": request.workspace,
                "state_abbr": request.state_abbr,
                "timestamp": datetime.now().isoformat(),
                "use_clusters": request.use_clusters,
                "start_date": request.start_date.isoformat() if request.start_date else None,
                "end_date": request.end_date.isoformat() if request.end_date else None,
                "teams": request.team_config.teams,
                "max_route_minutes": request.max_route_minutes,
                "service_minutes_per_site": request.service_minutes_per_site
            },
            "result": result.model_dump(mode='json', warnings=False)
        }
        
        # Save complete JSON output with metadata
        json_file = output_dir / f"route_plan_{timestamp}.json"
        with open(json_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"✓ Results saved to: {json_file}")
        
        # Auto-generate Folium map visualization
        try:
            from planning_engine.visualization import generate_folium_map
            map_file = output_dir / f"route_map_{timestamp}.html"
            generate_folium_map(result, map_file)
            print(f"✓ Map generated: {map_file}")
        except Exception as e:
            print(f"⚠ Warning: Could not generate map: {e}")
    
    return result
