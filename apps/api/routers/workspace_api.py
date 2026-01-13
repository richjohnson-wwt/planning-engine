"""
Workspace Management API Router
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form
from pydantic import BaseModel
from pathlib import Path
import logging
import json
import tempfile
import os

from planning_engine import new_workspace, parse_excel
from planning_engine.paths import get_project_root

# Import authentication utilities
try:
    from ..auth import UserInDB, get_current_user
except ImportError:
    from auth import UserInDB, get_current_user

# Import context management for user-scoped workspaces
from planning_engine.paths import set_current_username

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


# Dependency to set username context for all authenticated requests
async def set_user_context(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """Set the username context for user-scoped workspace paths."""
    set_current_username(current_user.username)
    return current_user


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


@router.get("")
def list_workspaces(current_user: UserInDB = Depends(set_user_context)):
    """List all existing workspaces for the authenticated user"""
    logger = logging.getLogger(__name__)
    
    # Workspace directory is automatically user-scoped via context
    workspace_dir = get_project_root() / "workspace"
    logger.info(f"Listing workspaces for user '{current_user.username}' from: {workspace_dir}")
    
    # Create the workspace directory if it doesn't exist
    if not workspace_dir.exists():
        logger.info(f"Creating workspace directory for user '{current_user.username}': {workspace_dir}")
        workspace_dir.mkdir(parents=True, exist_ok=True)
        return {"workspaces": []}
    
    # Get all subdirectories in user's workspace directory
    workspaces = [
        d.name for d in workspace_dir.iterdir() 
        if d.is_dir() and not d.name.startswith('.')
    ]
    
    logger.info(f"Found {len(workspaces)} workspaces for user '{current_user.username}': {workspaces}")
    return {"workspaces": sorted(workspaces)}


@router.get("/{workspace_name}/states")
def list_workspace_states(workspace_name: str, current_user: UserInDB = Depends(set_user_context)):
    """List all state subdirectories with detailed information (site count, geocode status, cluster count, error count)"""
    import pandas as pd
    from planning_engine.core.workspace import get_workspace_path
    
    # Use context-based workspace path (automatically user-scoped)
    workspace_path = get_workspace_path(workspace_name)
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
        geocoded_errors_csv = cache_dir / state_name / "geocoded-errors.csv"
        clustered_csv = cache_dir / state_name / "clustered.csv"
        
        # Count sites from addresses.csv
        site_count = 0
        if addresses_csv.exists():
            try:
                df = pd.read_csv(addresses_csv)
                site_count = len(df)
            except Exception:
                site_count = 0
        
        # Check if geocoded (either geocoded.csv exists OR geocoded-errors.csv exists)
        # This means geocoding has been attempted
        geocoded = geocoded_csv.exists() or geocoded_errors_csv.exists()
        
        # Count geocoding errors from geocoded-errors.csv
        error_count = 0
        if geocoded_errors_csv.exists():
            try:
                df_errors = pd.read_csv(geocoded_errors_csv)
                error_count = len(df_errors)
            except Exception:
                error_count = 0
        
        # Get cluster count from clustered.csv
        cluster_count = None
        if clustered_csv.exists():
            try:
                df = pd.read_csv(clustered_csv)
                if 'cluster_id' in df.columns:
                    cluster_count = df['cluster_id'].nunique()
            except Exception:
                cluster_count = None
        
        states_info.append({
            "name": state_name,
            "site_count": site_count,
            "geocoded": geocoded,
            "geocode_errors": error_count,
            "cluster_count": cluster_count
        })
    
    return {"states": states_info}


@router.post("", response_model=WorkspaceResponse)
def create_workspace(request: WorkspaceRequest, current_user: UserInDB = Depends(set_user_context)):
    """Create a new workspace for organizing planning workflows"""
    logger = logging.getLogger(__name__)
    logger.info(f"Creating workspace '{request.workspace_name}' for user '{current_user.username}'")
    
    workspace_path = new_workspace(request.workspace_name)
    logger.info(f"Workspace created at: {workspace_path}")
    
    return WorkspaceResponse(
        workspace_path=str(workspace_path),
        message=f"Workspace '{request.workspace_name}' created successfully"
    )


@router.post("/parse-excel", response_model=ParseExcelResponse)
def parse_excel_file(request: ParseExcelRequest, current_user: UserInDB = Depends(set_user_context)):
    """Parse an Excel file and map columns to standard fields, organized by state"""
    from fastapi import HTTPException
    
    try:
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
    except ValueError as e:
        # Column mapping errors or validation errors
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Unexpected errors
        raise HTTPException(status_code=500, detail=f"Failed to parse Excel file: {str(e)}")


@router.post("/parse-excel-upload", response_model=ParseExcelResponse)
async def parse_excel_upload(
    file: UploadFile = File(...),
    workspace_name: str = Form(...),
    sheet_name: str = Form(""),
    current_user: UserInDB = Depends(set_user_context),
    column_mapping: str = Form(...)
):
    """Parse an uploaded Excel file and map columns to standard fields, organized by state"""
    from fastapi import HTTPException
    
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
    except ValueError as e:
        # Column mapping errors or validation errors
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Unexpected errors
        raise HTTPException(status_code=500, detail=f"Failed to parse Excel file: {str(e)}")
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)
