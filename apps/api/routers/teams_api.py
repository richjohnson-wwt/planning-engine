"""
Team Management and Schedule Generation API Router
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from datetime import date, datetime
import tempfile
import zipfile
import json

from planning_engine.team_management import (
    load_teams, add_team, update_team, delete_team,
    generate_team_id, get_available_cities
)
from planning_engine.models import Team, TeamListResponse
from planning_engine.core.workspace import validate_workspace, get_workspace_path

# Import authentication utilities
try:
    from ..auth import UserInDB, get_current_user
except ImportError:
    from auth import UserInDB, get_current_user

# Import context management for user-scoped workspaces
from planning_engine.paths import set_current_username

router = APIRouter(prefix="/workspaces", tags=["teams"])


# Dependency to set username context for all authenticated requests
async def set_user_context(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """Set the username context for user-scoped workspace paths."""
    set_current_username(current_user.username)
    return current_user


@router.get("/{workspace_name}/states/{state_abbr}/teams")
def list_teams(workspace_name: str, state_abbr: str, current_user: UserInDB = Depends(set_user_context)):
    """
    List all teams for a workspace and state.
    
    Returns list of teams with their details.
    """
    try:
        teams = load_teams(workspace_name, state_abbr)
        return TeamListResponse(teams=teams, total_teams=len(teams))
    except Exception as e:
        return {"error": str(e), "teams": [], "total_teams": 0}


@router.post("/{workspace_name}/states/{state_abbr}/teams")
def create_team(workspace_name: str, state_abbr: str, team: dict, current_user: UserInDB = Depends(set_user_context)):
    """
    Create a new team for a workspace and state.
    
    If team_id is not provided, it will be auto-generated.
    """
    try:
        # Auto-generate team_id if not provided
        if not team.get('team_id'):
            team['team_id'] = generate_team_id(workspace_name, state_abbr)
        
        # Set created_date if not provided
        if not team.get('created_date'):
            team['created_date'] = date.today().isoformat()
        
        # Create Team object
        team_obj = Team(**team)
        
        # Add team
        added_team = add_team(workspace_name, state_abbr, team_obj)
        
        return {"success": True, "team": added_team}
    
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Failed to create team: {str(e)}"}


@router.put("/{workspace_name}/states/{state_abbr}/teams/{team_id}")
def update_team_endpoint(workspace_name: str, state_abbr: str, team_id: str, team: dict, current_user: UserInDB = Depends(set_user_context)):
    """
    Update an existing team.
    """
    try:
        # Ensure team_id in body matches URL parameter
        team['team_id'] = team_id
        
        # Create Team object
        team_obj = Team(**team)
        
        # Update team
        updated_team = update_team(workspace_name, state_abbr, team_id, team_obj)
        
        return {"success": True, "team": updated_team}
    
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Failed to update team: {str(e)}"}


@router.delete("/{workspace_name}/states/{state_abbr}/teams/{team_id}")
def delete_team_endpoint(workspace_name: str, state_abbr: str, team_id: str, current_user: UserInDB = Depends(set_user_context)):
    """
    Delete a team.
    """
    try:
        success = delete_team(workspace_name, state_abbr, team_id)
        
        if success:
            return {"success": True, "message": f"Team {team_id} deleted"}
        else:
            return {"success": False, "error": f"Team {team_id} not found"}
    
    except Exception as e:
        return {"success": False, "error": f"Failed to delete team: {str(e)}"}


@router.get("/{workspace_name}/states/{state_abbr}/teams/generate-id")
def generate_team_id_endpoint(workspace_name: str, state_abbr: str, current_user: UserInDB = Depends(set_user_context)):
    """
    Generate a unique team ID for a state.
    
    Useful for UI to pre-populate team_id field.
    """
    try:
        team_id = generate_team_id(workspace_name, state_abbr)
        return {"team_id": team_id}
    except Exception as e:
        return {"error": str(e)}


@router.get("/{workspace_name}/states/{state_abbr}/cities")
def get_cities(workspace_name: str, state_abbr: str, current_user: UserInDB = Depends(set_user_context)):
    """
    Get list of available cities for a state from geocoded data.
    Used to populate city dropdown when creating teams.
    """
    try:
        cities = get_available_cities(workspace_name, state_abbr)
        return {"cities": cities}
    except Exception as e:
        return {"error": str(e), "cities": []}


@router.get("/{workspace_name}/states/{state_abbr}/planning-team-ids")
def get_planning_team_ids(workspace_name: str, state_abbr: str, current_user: UserInDB = Depends(set_user_context)):
    """
    Get unique Team IDs from the latest planning result for a state.
    Used to populate Team ID dropdown when creating teams.
    
    Returns list of unique team IDs from the most recent planning output.
    If no planning result exists, returns empty list.
    """
    try:
        workspace_path = validate_workspace(workspace_name)
        output_dir = workspace_path / "output" / state_abbr
        
        if not output_dir.exists():
            return {"team_ids": [], "message": "No planning results found. Run a plan first."}
        
        # Find the most recent route_plan_*.json file
        plan_files = sorted(output_dir.glob("route_plan_*.json"), reverse=True)
        
        if not plan_files:
            return {"team_ids": [], "message": "No planning results found. Run a plan first."}
        
        # Load the most recent plan
        latest_plan = plan_files[0]
        with open(latest_plan, 'r') as f:
            plan_data = json.load(f)
        
        # Extract unique team IDs from team_days
        team_ids = set()
        result = plan_data.get('result', {})
        team_days = result.get('team_days', [])
        
        for team_day in team_days:
            # Try team_label first (e.g., "C1-T1"), fall back to team_id
            team_id = team_day.get('team_label') or str(team_day.get('team_id', ''))
            if team_id:
                team_ids.add(team_id)
        
        # Convert to sorted list
        team_ids_list = sorted(list(team_ids))
        
        return {
            "team_ids": team_ids_list,
            "message": f"Found {len(team_ids_list)} unique team(s) from latest plan"
        }
    
    except Exception as e:
        return {"team_ids": [], "error": str(e)}


@router.get("/{workspace_name}/states/{state_abbr}/teams/{team_id}/schedule")
async def generate_team_schedule(
    workspace_name: str, 
    state_abbr: str, 
    team_id: str,
    current_user: UserInDB = Depends(set_user_context)
):
    """
    Generate a schedule for a specific team (PDF or Text format).
    
    Returns the schedule file for download.
    Requires that:
    1. A planning result exists for the workspace/state
    2. The team exists in teams.csv
    3. The team has assigned routes in the planning result
    """
    from planning_engine.team_schedule import generate_team_schedule_pdf, generate_team_schedule_text
    
    try:
        # Create temporary file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_dir = Path(tempfile.gettempdir())
        # Sanitize team_id for filename (replace commas with underscores to avoid HTTP header issues)
        safe_team_id = team_id.replace(',', '_')
        
        # Toggle between PDF and Text formats for demo
        use_pdf = False  # Set to False to demo text format
        
        print(f"DEBUG: use_pdf = {use_pdf}")  # Debug logging
        
        if use_pdf:
            # Generate PDF
            filename = f"schedule_{safe_team_id}_{timestamp}.pdf"
            file_path = temp_dir / filename
            success = generate_team_schedule_pdf(
                workspace_name,
                state_abbr,
                team_id,
                file_path
            )
            media_type = "application/pdf"
        else:
            # Generate Text
            filename = f"schedule_{safe_team_id}_{timestamp}.txt"
            file_path = temp_dir / filename
            success = generate_team_schedule_text(
                workspace_name,
                state_abbr,
                team_id,
                file_path
            )
            media_type = "text/plain"
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Could not generate schedule for team {team_id}. Check that planning results exist and team has assigned routes."
            )
        
        # Return file
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate schedule: {str(e)}"
        )


@router.get("/{workspace_name}/states/{state_abbr}/teams/schedules/all")
async def generate_all_team_schedules(
    workspace_name: str,
    state_abbr: str,
    current_user: UserInDB = Depends(set_user_context)
):
    """
    Generate PDF schedules for all teams in a state.
    
    Returns a ZIP file containing all team schedule PDFs.
    """
    from planning_engine.team_schedule import generate_all_team_schedules
    
    try:
        # Create temporary directory for PDFs
        temp_dir = Path(tempfile.mkdtemp())
        
        # Generate all schedules
        generated_files = generate_all_team_schedules(
            workspace_name,
            state_abbr,
            output_dir=temp_dir
        )
        
        if not generated_files:
            raise HTTPException(
                status_code=404,
                detail="No schedules could be generated. Check that planning results and teams exist."
            )
        
        # Create ZIP file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"team_schedules_{state_abbr}_{timestamp}.zip"
        zip_path = temp_dir / zip_filename
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for team_id, pdf_path in generated_files.items():
                zipf.write(pdf_path, pdf_path.name)
        
        # Return ZIP file
        return FileResponse(
            path=str(zip_path),
            filename=zip_filename,
            media_type="application/zip",
            headers={
                "Content-Disposition": f"attachment; filename={zip_filename}"
            }
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate schedules: {str(e)}"
        )
