"""
Route Planning API Router
"""
from fastapi import APIRouter, Depends
from pathlib import Path
import json
from datetime import datetime
import logging

from planning_engine import plan
from planning_engine.models import PlanRequest, PlanResult

# Import authentication utilities
try:
    from ..auth import UserInDB, get_current_user
except ImportError:
    from auth import UserInDB, get_current_user

# Import context management for user-scoped workspaces
from planning_engine.paths import set_current_username

router = APIRouter(tags=["planning"])


# Dependency to set username context for all authenticated requests
async def set_user_context(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """Set the username context for user-scoped workspace paths."""
    set_current_username(current_user.username)
    return current_user


@router.post("/plan", response_model=PlanResult)
def run_plan(request: PlanRequest, current_user: UserInDB = Depends(set_user_context)):
    """
    Plan routes for teams/crews to visit sites.
    
    Results are automatically saved to the workspace output folder organized by state:
    - data/workspace/{workspace}/output/{STATE}/route_plan_{timestamp}.json
    
    JSON includes metadata wrapper with request parameters and planning results.
    """
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
        from planning_engine.core.workspace import get_workspace_path
        
        # Create state-specific output directory (matching cache structure)
        # Use context-based workspace path (automatically user-scoped)
        workspace_path = get_workspace_path(request.workspace)
        output_dir = workspace_path / "output" / request.state_abbr
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
        
        # Initialize/update progress tracking
        try:
            from planning_engine.progress_tracking import (
                initialize_progress_from_geocoded,
                sync_progress_with_plan_result
            )
            
            # Initialize progress.csv if it doesn't exist (adds new sites)
            sites_added = initialize_progress_from_geocoded(request.workspace, force_refresh=True)
            if sites_added > 0:
                print(f"✓ Progress tracking initialized: {sites_added} new sites added")
            
            # Sync crew assignments from planning results
            updated_count = sync_progress_with_plan_result(request.workspace, result.model_dump())
            if updated_count > 0:
                print(f"✓ Progress updated: {updated_count} sites assigned to crews")
        except Exception as e:
            print(f"⚠ Warning: Could not update progress tracking: {e}")
    
    return result
