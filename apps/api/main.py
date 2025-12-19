from fastapi import FastAPI
from planning_engine import plan, new_workspace, parse_excel, geocode, cluster
from planning_engine.models import PlanRequest, PlanResult
from pydantic import BaseModel

app = FastAPI(title="Planning Engine API")


class WorkspaceRequest(BaseModel):
    workspace_name: str


class WorkspaceResponse(BaseModel):
    workspace_path: str
    message: str


class ParseExcelRequest(BaseModel):
    workspace_name: str
    file_path: str
    column_mapping: dict[str, str]
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "workspace_name": "my_project_2025",
                    "file_path": "/Users/johnsori/Downloads/AscensionClean.xlsx",
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
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "workspace_name": "my_project_2025"
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
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "workspace_name": "my_project_2025"
                }
            ]
        }
    }


class ClusterResponse(BaseModel):
    output_path: str
    message: str
    sites_clustered: int
    num_clusters: int


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
    """Parse an Excel file and map columns to standard fields"""
    output_path = parse_excel(
        workspace_name=request.workspace_name,
        file_path=request.file_path,
        column_mapping=request.column_mapping
    )
    return ParseExcelResponse(
        output_path=str(output_path),
        message=f"Excel file parsed successfully. Output saved to {output_path}"
    )


@app.post("/geocode", response_model=GeocodeResponse)
def geocode_addresses(request: GeocodeRequest):
    """Geocode addresses from workspace's addresses.csv file"""
    import pandas as pd
    output_path = geocode(workspace_name=request.workspace_name)
    
    # Count how many addresses were geocoded
    df = pd.read_csv(output_path)
    addresses_count = len(df)
    
    return GeocodeResponse(
        output_path=str(output_path),
        message=f"Geocoding completed. Results saved to {output_path}",
        addresses_geocoded=addresses_count
    )


@app.post("/cluster", response_model=ClusterResponse)
def cluster_sites(request: ClusterRequest):
    """Cluster geocoded sites based on geographic coordinates"""
    import pandas as pd
    output_path = cluster(workspace_name=request.workspace_name)
    
    # Get cluster statistics
    df = pd.read_csv(output_path)
    sites_count = len(df)
    num_clusters = len(df[df['cluster_id'] >= 0]['cluster_id'].unique())
    
    return ClusterResponse(
        output_path=str(output_path),
        message=f"Clustering completed. {sites_count} sites assigned to {num_clusters} clusters",
        sites_clustered=sites_count,
        num_clusters=num_clusters
    )


@app.post("/plan", response_model=PlanResult)
def run_plan(request: PlanRequest):
    return plan(request)
