"""
Clustering API Router
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
import pandas as pd

from planning_engine import cluster, get_cluster_info

# Import authentication utilities
try:
    from ..auth import UserInDB, get_current_user
except ImportError:
    from auth import UserInDB, get_current_user

# Import context management for user-scoped workspaces
from planning_engine.paths import set_current_username

router = APIRouter(tags=["clustering"])


# Dependency to set username context for all authenticated requests
async def set_user_context(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """Set the username context for user-scoped workspace paths."""
    set_current_username(current_user.username)
    return current_user


class ClusterRequest(BaseModel):
    workspace_name: str
    state_abbr: str
    max_diameter_miles: float = 100
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "workspace_name": "my_project_2025",
                    "state_abbr": "LA",
                    "max_diameter_miles": 100
                }
            ]
        }
    }


class ClusterResponse(BaseModel):
    output_path: str
    message: str
    sites_clustered: int
    num_clusters: int
    max_diameter_miles: float


@router.post("/cluster", response_model=ClusterResponse)
def cluster_sites(request: ClusterRequest, current_user: UserInDB = Depends(set_user_context)):
    """
    Cluster geocoded sites based on geographic coordinates with diameter constraints.
    
    The max_diameter_miles parameter controls how geographically spread clusters can be:
    - Tight (50-75 miles): Dense urban areas, shorter workdays, more focused territories
    - Normal (100 miles): Recommended default for most scenarios
    - Loose (125-150 miles): Rural areas with sparse sites, longer workdays
    """
    output_path = cluster(
        workspace_name=request.workspace_name, 
        state_abbr=request.state_abbr,
        max_diameter_miles=request.max_diameter_miles
    )
    
    # Get cluster statistics
    df = pd.read_csv(output_path)
    sites_count = len(df)
    num_clusters = len(df[df['cluster_id'] >= 0]['cluster_id'].unique())
    
    return ClusterResponse(
        output_path=str(output_path),
        message=f"Clustering completed for state '{request.state_abbr}'. {sites_count} sites assigned to {num_clusters} clusters (max diameter: {request.max_diameter_miles} miles)",
        sites_clustered=sites_count,
        num_clusters=num_clusters,
        max_diameter_miles=request.max_diameter_miles
    )


@router.get("/workspaces/{workspace_name}/states/{state_abbr}/cluster-info")
def get_cluster_info_endpoint(workspace_name: str, state_abbr: str, current_user: UserInDB = Depends(set_user_context)):
    """
    Get cluster information for a workspace and state.
    
    Returns cluster count, total sites, and cluster size distribution.
    Used by the UI to determine appropriate team count constraints.
    """
    cluster_info = get_cluster_info(workspace_name, state_abbr)
    
    if cluster_info is None:
        return {
            "error": "Failed to retrieve cluster information",
            "clustered_file_exists": False
        }
    
    return cluster_info
