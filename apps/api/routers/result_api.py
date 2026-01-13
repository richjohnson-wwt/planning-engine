"""
Output File Management API Router
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
import json

from planning_engine.core.workspace import get_workspace_path

# Import authentication utilities
try:
    from ..auth import UserInDB, get_current_user, get_current_user_optional_token
except ImportError:
    from auth import UserInDB, get_current_user, get_current_user_optional_token

# Import context management for user-scoped workspaces
from planning_engine.paths import set_current_username

router = APIRouter(prefix="/workspaces", tags=["results"])


# Dependency to set username context for all authenticated requests
async def set_user_context(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """Set the username context for user-scoped workspace paths."""
    set_current_username(current_user.username)
    return current_user


@router.get("/{workspace_name}/output/{state_abbr}/latest")
def get_latest_result(workspace_name: str, state_abbr: str, current_user: UserInDB = Depends(set_user_context)):
    """
    Get the latest planning result JSON for a workspace and state.
    
    Returns the most recent route_plan_*.json file with metadata and results.
    
    NOTE: This route must be defined BEFORE the /{filename} route to avoid
    FastAPI matching "latest" as a filename.
    """
    # Use context-based workspace path (automatically user-scoped)
    workspace_path = get_workspace_path(workspace_name)
    output_dir = workspace_path / "output" / state_abbr
    
    if not output_dir.exists():
        return {"error": "No results found", "result": None}
    
    # Find all JSON result files
    json_files = [
        f for f in output_dir.iterdir()
        if f.is_file() and f.name.startswith("route_plan_") and f.suffix == ".json"
    ]
    
    if not json_files:
        return {"error": "No results found", "result": None}
    
    # Get the most recent file by modification time
    latest_file = max(json_files, key=lambda f: f.stat().st_mtime)
    
    try:
        with open(latest_file, 'r') as f:
            data = json.load(f)
        
        # Return both metadata and result
        return {
            "metadata": data.get("metadata", {}),
            "result": data.get("result", {})
        }
    except Exception as e:
        return {"error": f"Failed to load result: {str(e)}", "result": None}


@router.get("/{workspace_name}/output/{state_abbr}/{filename}")
async def get_output_file(
    workspace_name: str, 
    state_abbr: str, 
    filename: str, 
    token: str = None,
    current_user: UserInDB = Depends(get_current_user_optional_token)
):
    """
    Serve output files (HTML maps, JSON results) from workspace output directory.
    
    Supports both Authorization header and ?token=xxx query parameter for HTML files.
    Example: GET /workspaces/foo/output/LA/route_map_20231223_120000.html?token=xxx
    """
    # Set username context for user-scoped paths
    set_current_username(current_user.username)
    
    # Construct the file path using context-based workspace path
    workspace_path = get_workspace_path(workspace_name)
    output_dir = workspace_path / "output" / state_abbr
    file_path = output_dir / filename
    
    # Security check: ensure the resolved path is within the output directory
    try:
        file_path = file_path.resolve()
        output_dir = output_dir.resolve()
        if not str(file_path).startswith(str(output_dir)):
            return {"error": "Invalid file path"}
    except Exception as e:
        return {"error": f"Invalid path: {str(e)}"}
    
    # Check if file exists
    if not file_path.exists():
        return {"error": f"File not found: {filename}"}
    
    # Determine media type based on extension
    media_type = "text/html" if filename.endswith(".html") else "application/json"
    
    return FileResponse(file_path, media_type=media_type)


@router.delete("/{workspace_name}/output/{state_abbr}/{filename}")
def delete_output_file(
    workspace_name: str,
    state_abbr: str,
    filename: str,
    current_user: UserInDB = Depends(set_user_context)
):
    """
    Delete an output file (HTML map or JSON result) from workspace output directory.
    
    Returns success status and message.
    """
    try:
        workspace_path = get_workspace_path(workspace_name)
        output_dir = workspace_path / "output" / state_abbr
        file_path = output_dir / filename
        
        # Security check: ensure the resolved path is within the output directory
        try:
            file_path = file_path.resolve()
            output_dir = output_dir.resolve()
            if not str(file_path).startswith(str(output_dir)):
                raise HTTPException(status_code=400, detail="Invalid file path")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid path: {str(e)}")
        
        # Check if file exists
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {filename}")
        
        # Delete the file
        file_path.unlink()
        
        return {
            "success": True,
            "message": f"File '{filename}' deleted successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")


@router.get("/{workspace_name}/output/{state_abbr}")
def list_output_files(workspace_name: str, state_abbr: str, current_user: UserInDB = Depends(set_user_context)):
    """
    List all output files for a workspace and state.
    
    Returns a list of available HTML maps and JSON result files.
    """
    # Use context-based workspace path (automatically user-scoped)
    workspace_path = get_workspace_path(workspace_name)
    output_dir = workspace_path / "output" / state_abbr
    
    if not output_dir.exists():
        return {"files": []}
    
    files = []
    for file_path in output_dir.iterdir():
        if file_path.is_file() and file_path.suffix in [".html", ".json"]:
            files.append({
                "filename": file_path.name,
                "type": "map" if file_path.suffix == ".html" else "result",
                "size": file_path.stat().st_size,
                "modified": file_path.stat().st_mtime,
                "url": f"/api/workspaces/{workspace_name}/output/{state_abbr}/{file_path.name}"
            })
    
    # Sort by modified time, newest first
    files.sort(key=lambda x: x["modified"], reverse=True)
    
    return {"files": files}
