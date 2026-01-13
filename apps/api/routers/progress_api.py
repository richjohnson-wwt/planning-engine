"""
Progress Tracking API Router
"""
from fastapi import APIRouter, Depends
from datetime import datetime

from planning_engine.progress_tracking import (
    load_progress, initialize_progress_from_geocoded,
    update_site_progress, bulk_update_progress
)

# Import authentication utilities
try:
    from ..auth import UserInDB, get_current_user
except ImportError:
    from auth import UserInDB, get_current_user

# Import context management for user-scoped workspaces
from planning_engine.paths import set_current_username

router = APIRouter(prefix="/workspaces", tags=["progress"])


# Dependency to set username context for all authenticated requests
async def set_user_context(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """Set the username context for user-scoped workspace paths."""
    set_current_username(current_user.username)
    return current_user


@router.get("/{workspace_name}/progress")
def get_progress(workspace_name: str, state: str = None, current_user: UserInDB = Depends(set_user_context)):
    """
    Get progress tracking data for a workspace.
    
    Optional query parameter 'state' to filter by state abbreviation.
    If not provided, returns progress for all states.
    """
    try:
        response = load_progress(workspace_name, state_filter=state)
        return response
    except Exception as e:
        return {
            "error": str(e),
            "progress": [],
            "total_sites": 0,
            "by_status": {}
        }


@router.post("/{workspace_name}/progress/init")
def initialize_progress(workspace_name: str, force_refresh: bool = False, current_user: UserInDB = Depends(set_user_context)):
    """
    Initialize progress tracking from geocoded sites.
    
    Scans all cache/{state}/geocoded.csv files and creates progress.csv
    with 'pending' status for all sites.
    
    Query parameter 'force_refresh' will re-scan and add any new sites.
    """
    try:
        sites_added = initialize_progress_from_geocoded(workspace_name, force_refresh)
        return {
            "success": True,
            "message": f"Initialized progress tracking for {sites_added} sites",
            "sites_added": sites_added
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "sites_added": 0
        }


@router.put("/{workspace_name}/progress/{site_id}")
def update_progress(workspace_name: str, site_id: str, update_data: dict, current_user: UserInDB = Depends(set_user_context)):
    """
    Update progress for a single site.
    
    Accepts partial updates - only provided fields will be updated.
    """
    try:
        # Extract update fields
        status = update_data.get('status')
        scheduled_date = update_data.get('scheduled_date')
        crew_assigned = update_data.get('crew_assigned')
        notes = update_data.get('notes')
        
        # Convert scheduled_date string to date if provided
        if scheduled_date:
            scheduled_date = datetime.fromisoformat(scheduled_date).date()
        
        updated_site = update_site_progress(
            workspace_name,
            site_id,
            status=status,
            scheduled_date=scheduled_date,
            crew_assigned=crew_assigned,
            notes=notes
        )
        
        return {"success": True, "site": updated_site}
    
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Failed to update progress: {str(e)}"}


@router.put("/{workspace_name}/progress/bulk")
def bulk_update_progress_endpoint(workspace_name: str, update_data: dict, current_user: UserInDB = Depends(set_user_context)):
    """
    Bulk update progress for multiple sites.
    
    Request body should include:
    - site_ids: List of site IDs to update
    - status: Optional new status
    - scheduled_date: Optional scheduled date
    - crew_assigned: Optional crew assignment
    - notes: Optional notes
    """
    try:
        site_ids = update_data.get('site_ids', [])
        status = update_data.get('status')
        scheduled_date = update_data.get('scheduled_date')
        crew_assigned = update_data.get('crew_assigned')
        notes = update_data.get('notes')
        
        # Convert scheduled_date string to date if provided
        if scheduled_date:
            scheduled_date = datetime.fromisoformat(scheduled_date).date()
        
        updated_count = bulk_update_progress(
            workspace_name,
            site_ids,
            status=status,
            scheduled_date=scheduled_date,
            crew_assigned=crew_assigned,
            notes=notes
        )
        
        return {
            "success": True,
            "message": f"Updated {updated_count} sites",
            "updated_count": updated_count
        }
    
    except Exception as e:
        return {"success": False, "error": f"Failed to bulk update: {str(e)}"}
