from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from planning_engine import plan, new_workspace, parse_excel, geocode, cluster, get_cluster_info
from planning_engine.models import PlanRequest, PlanResult
from planning_engine.paths import get_project_root
from pydantic import BaseModel
from pathlib import Path
import warnings
import logging
import json
import tempfile
from datetime import timedelta

# Import authentication utilities
# Try relative import first (for production/module mode), fall back to absolute (for dev)
try:
    from .auth import (
        authenticate_user, create_access_token, get_current_user, get_current_user_optional_token,
        get_current_admin_user, create_user, delete_user, list_users, User, UserInDB,
        Token, LoginRequest, CreateUserRequest, ACCESS_TOKEN_EXPIRE_DAYS
    )
except ImportError:
    from auth import (
        authenticate_user, create_access_token, get_current_user, get_current_user_optional_token,
        get_current_admin_user, create_user, delete_user, list_users, User, UserInDB,
        Token, LoginRequest, CreateUserRequest, ACCESS_TOKEN_EXPIRE_DAYS
    )

# Import context management for user-scoped workspaces
from planning_engine.paths import set_current_username, clear_current_username

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Suppress Pydantic serialization warnings for optional date fields
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic.type_adapter")

app = FastAPI(title="Planning Engine API")

# Add CORS middleware to allow requests from the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Local development
        "http://localhost:8080",
        "*",  # Allow all origins for internal deployment
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Authentication Endpoints
# ============================================================================

@app.post("/auth/login", response_model=Token)
def login(login_request: LoginRequest):
    """
    Login endpoint - returns JWT token with long expiration (90 days).
    
    Default admin credentials:
    - username: admin
    - password: admin123
    """
    user = authenticate_user(login_request.username, login_request.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )
    
    # Create access token with long expiration
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        username=user.username
    )


@app.post("/auth/logout")
def logout(current_user: UserInDB = Depends(get_current_user)):
    """
    Logout endpoint - client should discard the token.
    Server doesn't track tokens, so this is just for client-side cleanup.
    """
    return {"message": "Logged out successfully"}


@app.get("/auth/me", response_model=User)
def get_current_user_info(current_user: UserInDB = Depends(get_current_user)):
    """Get current authenticated user information."""
    return current_user


@app.get("/auth/users", response_model=list[User])
def get_users(current_user: UserInDB = Depends(get_current_admin_user)):
    """List all users (admin only)."""
    return list_users()


@app.post("/auth/users", response_model=User)
def create_new_user(
    user_request: CreateUserRequest,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Create a new user (admin only)."""
    try:
        user = create_user(
            username=user_request.username,
            password=user_request.password,
            is_admin=user_request.is_admin
        )
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/auth/users/{username}")
def delete_user_endpoint(
    username: str,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Delete a user (admin only)."""
    if username == current_user.username:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    try:
        success = delete_user(username)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        return {"message": f"User '{username}' deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Dependency to set username context for all authenticated requests
async def set_user_context(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """Set the username context for user-scoped workspace paths."""
    set_current_username(current_user.username)
    return current_user


# ============================================================================
# Workspace and Data Endpoints (now require authentication)
# ============================================================================

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


@app.get("/workspaces/{workspace_name}/states")
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


@app.post("/workspace", response_model=WorkspaceResponse)
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


@app.post("/parse-excel", response_model=ParseExcelResponse)
def parse_excel_file(request: ParseExcelRequest, current_user: UserInDB = Depends(set_user_context)):
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
    current_user: UserInDB = Depends(set_user_context),
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
def geocode_addresses(request: GeocodeRequest, current_user: UserInDB = Depends(set_user_context)):
    """Geocode addresses from workspace's state-specific addresses.csv file"""
    import pandas as pd
    from pathlib import Path
    
    try:
        output_path = geocode(workspace_name=request.workspace_name, state_abbr=request.state_abbr)
        
        # Count how many addresses were geocoded
        df = pd.read_csv(output_path)
        addresses_count = len(df)
        
        return GeocodeResponse(
            output_path=str(output_path),
            message=f"Geocoding completed for state '{request.state_abbr}'. {addresses_count} addresses successfully geocoded.",
            addresses_geocoded=addresses_count
        )
    except ValueError as e:
        # Geocoding completed but with some errors
        # The error message contains details about successful and failed geocodes
        error_msg = str(e)
        
        # Extract the output path from the workspace structure
        workspace_path = get_project_root() / "data" / "workspace" / request.workspace_name
        output_path = workspace_path / "cache" / request.state_abbr / "geocoded.csv"
        
        # Count successful geocodes
        addresses_count = 0
        if output_path.exists():
            df = pd.read_csv(output_path)
            addresses_count = len(df)
        
        # Return success response with warning message
        return GeocodeResponse(
            output_path=str(output_path),
            message=f"Geocoding completed for state '{request.state_abbr}' with errors. {error_msg}",
            addresses_geocoded=addresses_count
        )
# ============================================================================
# Geocoding Error Management Endpoints
# ============================================================================

class GeocodeErrorResponse(BaseModel):
    """Response model for geocoding errors"""
    errors: list[dict]
    count: int


class RetryGeocodeRequest(BaseModel):
    """Request to retry geocoding a single corrected address"""
    site_id: str
    street1: str
    street2: str = ""
    city: str
    state: str
    zip: str


class RetryGeocodeResponse(BaseModel):
    """Response from retrying geocoding"""
    success: bool
    lat: float | None = None
    lon: float | None = None
    message: str


@app.get("/workspaces/{workspace_name}/geocode-errors/{state_abbr}")
def get_geocode_errors(
    workspace_name: str, 
    state_abbr: str, 
    current_user: UserInDB = Depends(set_user_context)
):
    """
    Get list of geocoding errors for a specific state.
    
    Returns all addresses that failed geocoding from the geocoded-errors.csv file.
    """
    import pandas as pd
    from planning_engine.paths import get_workspace_path
    
    try:
        workspace_path = get_workspace_path(workspace_name)
        error_path = workspace_path / "cache" / state_abbr / "geocoded-errors.csv"
        
        if not error_path.exists():
            return GeocodeErrorResponse(errors=[], count=0)
        
        df = pd.read_csv(error_path)
        
        # Convert DataFrame to list of dicts
        errors = df.to_dict('records')
        
        return GeocodeErrorResponse(
            errors=errors,
            count=len(errors)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load geocoding errors: {str(e)}")


@app.post("/workspaces/{workspace_name}/geocode-errors/{state_abbr}/retry")
def retry_geocode_address(
    workspace_name: str,
    state_abbr: str,
    request: RetryGeocodeRequest,
    current_user: UserInDB = Depends(set_user_context)
):
    """
    Retry geocoding for a single corrected address.
    
    If successful, the address is:
    1. Added to geocoded.csv
    2. Removed from geocoded-errors.csv
    """
    import pandas as pd
    from planning_engine.paths import get_workspace_path
    from planning_engine.data_prep.geocode import batch_geocode_sites
    
    try:
        workspace_path = get_workspace_path(workspace_name)
        cache_dir = workspace_path / "cache" / state_abbr
        geocoded_path = cache_dir / "geocoded.csv"
        error_path = cache_dir / "geocoded-errors.csv"
        
        # Build full address string
        address_parts = [request.street1]
        if request.street2:
            address_parts.append(request.street2)
        address_parts.extend([request.city, request.state, request.zip])
        full_address = ", ".join(address_parts)
        
        # Geocode the single address
        geocode_results = batch_geocode_sites([full_address])
        result = geocode_results[0] if geocode_results else None
        
        if not result or 'lat' not in result or 'lon' not in result:
            return RetryGeocodeResponse(
                success=False,
                message="Address could not be geocoded. Please verify the address is correct."
            )
        
        lat = result['lat']
        lon = result['lon']
        
        # Create new row with geocoded data
        new_row = {
            'site_id': request.site_id,
            'street1': request.street1,
            'street2': request.street2,
            'city': request.city,
            'state': request.state,
            'zip': request.zip,
            'lat': lat,
            'lon': lon
        }
        
        # Add to geocoded.csv
        if geocoded_path.exists():
            df_geocoded = pd.read_csv(geocoded_path)
            # Remove if already exists (in case of re-geocoding)
            df_geocoded = df_geocoded[df_geocoded['site_id'] != request.site_id]
            df_geocoded = pd.concat([df_geocoded, pd.DataFrame([new_row])], ignore_index=True)
        else:
            df_geocoded = pd.DataFrame([new_row])
        
        df_geocoded.to_csv(geocoded_path, index=False)
        
        # Also add to clustered.csv if it exists (assign to nearest cluster)
        clustered_path = workspace_path / "cache" / state_abbr / "clustered.csv"
        if clustered_path.exists():
            try:
                df_clustered = pd.read_csv(clustered_path)
                
                # Remove if already exists
                df_clustered = df_clustered[df_clustered['site_id'] != request.site_id]
                
                # Assign to nearest cluster based on coordinates
                if 'cluster_id' in df_clustered.columns and len(df_clustered) > 0:
                    from sklearn.metrics.pairwise import euclidean_distances
                    import numpy as np
                    
                    # Get cluster centroids
                    cluster_centroids = df_clustered.groupby('cluster_id')[['lat', 'lon']].mean()
                    
                    # Find nearest cluster
                    new_coords = np.array([[lat, lon]])
                    distances = euclidean_distances(new_coords, cluster_centroids.values)[0]
                    nearest_cluster = cluster_centroids.index[np.argmin(distances)]
                    
                    # Add to clustered.csv with cluster assignment
                    new_clustered_row = new_row.copy()
                    new_clustered_row['cluster_id'] = nearest_cluster
                    df_clustered = pd.concat([df_clustered, pd.DataFrame([new_clustered_row])], ignore_index=True)
                    df_clustered.to_csv(clustered_path, index=False)
            except Exception as e:
                # Log but don't fail if clustered update fails
                print(f"Warning: Failed to update clustered.csv: {e}")
        
        # Remove from geocoded-errors.csv
        if error_path.exists():
            df_errors = pd.read_csv(error_path)
            df_errors = df_errors[df_errors['site_id'] != request.site_id]
            
            if len(df_errors) > 0:
                df_errors.to_csv(error_path, index=False)
            else:
                # Delete error file if no more errors
                error_path.unlink()
        
        return RetryGeocodeResponse(
            success=True,
            lat=lat,
            lon=lon,
            message="Address successfully geocoded and added to geocoded.csv"
        )
    
    except Exception as e:
        return RetryGeocodeResponse(
            success=False,
            message=f"Error during geocoding: {str(e)}"
        )


@app.delete("/workspaces/{workspace_name}/geocode-errors/{state_abbr}/{site_id}")
def delete_geocode_error(
    workspace_name: str,
    state_abbr: str,
    site_id: str,
    current_user: UserInDB = Depends(set_user_context)
):
    """
    Remove a geocoding error from the error list.
    
    Use this when the user decides to exclude an address that cannot be fixed.
    """
    import pandas as pd
    from planning_engine.paths import get_workspace_path
    
    try:
        workspace_path = get_workspace_path(workspace_name)
        error_path = workspace_path / "cache" / state_abbr / "geocoded-errors.csv"
        
        if not error_path.exists():
            return {"success": True, "message": "Error file does not exist"}
        
        df_errors = pd.read_csv(error_path)
        original_count = len(df_errors)
        
        # Remove the specified site
        df_errors = df_errors[df_errors['site_id'] != site_id]
        
        if len(df_errors) == original_count:
            raise HTTPException(status_code=404, detail=f"Site ID '{site_id}' not found in errors")
        
        if len(df_errors) > 0:
            df_errors.to_csv(error_path, index=False)
        else:
            # Delete error file if no more errors
            error_path.unlink()
        
        return {
            "success": True,
            "message": f"Removed site '{site_id}' from geocoding errors"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete error: {str(e)}")


# ============================================================================
# Geocoded Site Editor Endpoints
# ============================================================================

class GeocodedSiteResponse(BaseModel):
    """Response model for a single geocoded site"""
    site_id: str
    street1: str
    street2: str = ""
    city: str
    state: str
    zip: str
    lat: float
    lon: float


class UpdateGeocodedSiteRequest(BaseModel):
    """Request to update a geocoded site"""
    street1: str
    street2: str = ""
    city: str
    state: str
    zip: str
    lat: float
    lon: float


@app.get("/workspaces/{workspace_name}/geocoded/{state_abbr}/{site_id}")
def get_geocoded_site(
    workspace_name: str,
    state_abbr: str,
    site_id: str,
    current_user: UserInDB = Depends(set_user_context)
):
    """
    Get a single geocoded site by site_id.
    
    Returns the site's address and coordinates from geocoded.csv.
    """
    import pandas as pd
    from planning_engine.paths import get_workspace_path
    
    try:
        workspace_path = get_workspace_path(workspace_name)
        geocoded_path = workspace_path / "cache" / state_abbr / "geocoded.csv"
        
        if not geocoded_path.exists():
            raise HTTPException(status_code=404, detail="Geocoded file not found. Run geocoding first.")
        
        df = pd.read_csv(geocoded_path)
        
        # Find the site
        site_row = df[df['site_id'] == site_id]
        
        if len(site_row) == 0:
            raise HTTPException(status_code=404, detail=f"Site ID '{site_id}' not found in geocoded data")
        
        # Convert to dict
        site_data = site_row.iloc[0].to_dict()
        
        # Ensure street2 exists
        if 'street2' not in site_data or pd.isna(site_data['street2']):
            site_data['street2'] = ''
        
        return GeocodedSiteResponse(
            site_id=str(site_data['site_id']),
            street1=str(site_data['street1']),
            street2=str(site_data['street2']),
            city=str(site_data['city']),
            state=str(site_data['state']),
            zip=str(site_data['zip']),
            lat=float(site_data['lat']),
            lon=float(site_data['lon'])
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load site: {str(e)}")


@app.put("/workspaces/{workspace_name}/geocoded/{state_abbr}/{site_id}")
def update_geocoded_site(
    workspace_name: str,
    state_abbr: str,
    site_id: str,
    request: UpdateGeocodedSiteRequest,
    current_user: UserInDB = Depends(set_user_context)
):
    """
    Update a geocoded site's address and/or coordinates.
    
    Updates the site in geocoded.csv with new data.
    """
    import pandas as pd
    from planning_engine.paths import get_workspace_path
    
    try:
        workspace_path = get_workspace_path(workspace_name)
        geocoded_path = workspace_path / "cache" / state_abbr / "geocoded.csv"
        
        if not geocoded_path.exists():
            raise HTTPException(status_code=404, detail="Geocoded file not found")
        
        df = pd.read_csv(geocoded_path)
        
        # Find the site
        site_index = df[df['site_id'] == site_id].index
        
        if len(site_index) == 0:
            raise HTTPException(status_code=404, detail=f"Site ID '{site_id}' not found")
        
        # Update the site data
        idx = site_index[0]
        df.at[idx, 'street1'] = request.street1
        df.at[idx, 'street2'] = request.street2
        df.at[idx, 'city'] = request.city
        df.at[idx, 'state'] = request.state
        df.at[idx, 'zip'] = request.zip
        df.at[idx, 'lat'] = request.lat
        df.at[idx, 'lon'] = request.lon
        
        # Save back to CSV
        df.to_csv(geocoded_path, index=False)
        
        # Also update clustered.csv if it exists (to keep it in sync)
        clustered_path = workspace_path / "cache" / state_abbr / "clustered.csv"
        if clustered_path.exists():
            try:
                df_clustered = pd.read_csv(clustered_path)
                clustered_site_index = df_clustered[df_clustered['site_id'] == site_id].index
                
                if len(clustered_site_index) > 0:
                    idx_clustered = clustered_site_index[0]
                    # Update all fields except cluster_id (preserve cluster assignment)
                    df_clustered.at[idx_clustered, 'street1'] = request.street1
                    df_clustered.at[idx_clustered, 'street2'] = request.street2
                    df_clustered.at[idx_clustered, 'city'] = request.city
                    df_clustered.at[idx_clustered, 'state'] = request.state
                    df_clustered.at[idx_clustered, 'zip'] = request.zip
                    df_clustered.at[idx_clustered, 'lat'] = request.lat
                    df_clustered.at[idx_clustered, 'lon'] = request.lon
                    
                    df_clustered.to_csv(clustered_path, index=False)
            except Exception as e:
                # Log but don't fail if clustered update fails
                print(f"Warning: Failed to update clustered.csv: {e}")
        
        return {
            "success": True,
            "message": f"Site '{site_id}' updated successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update site: {str(e)}")


@app.post("/cluster", response_model=ClusterResponse)
def cluster_sites(request: ClusterRequest, current_user: UserInDB = Depends(set_user_context)):
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


@app.get("/workspaces/{workspace_name}/states/{state_abbr}/cluster-info")
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


@app.post("/plan", response_model=PlanResult)
def run_plan(request: PlanRequest, current_user: UserInDB = Depends(set_user_context)):
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


@app.get("/workspaces/{workspace_name}/output/{state_abbr}/latest")
def get_latest_result(workspace_name: str, state_abbr: str, current_user: UserInDB = Depends(set_user_context)):
    """
    Get the latest planning result JSON for a workspace and state.
    
    Returns the most recent route_plan_*.json file with metadata and results.
    
    NOTE: This route must be defined BEFORE the /{filename} route to avoid
    FastAPI matching "latest" as a filename.
    """
    from planning_engine.core.workspace import get_workspace_path
    
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


@app.get("/workspaces/{workspace_name}/output/{state_abbr}/{filename}")
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
    import os
    from planning_engine.core.workspace import get_workspace_path
    
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


@app.get("/workspaces/{workspace_name}/output/{state_abbr}")
def list_output_files(workspace_name: str, state_abbr: str, current_user: UserInDB = Depends(set_user_context)):
    """
    List all output files for a workspace and state.
    
    Returns a list of available HTML maps and JSON result files.
    """
    from planning_engine.core.workspace import get_workspace_path
    
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


# ============================================================================
# TEAM MANAGEMENT ENDPOINTS
# ============================================================================

@app.get("/workspaces/{workspace_name}/states/{state_abbr}/teams")
def list_teams(workspace_name: str, state_abbr: str, current_user: UserInDB = Depends(set_user_context)):
    """
    List all teams for a workspace and state.
    
    Returns list of teams with their details.
    """
    from planning_engine.team_management import load_teams
    from planning_engine.models import TeamListResponse
    
    try:
        teams = load_teams(workspace_name, state_abbr)
        return TeamListResponse(teams=teams, total_teams=len(teams))
    except Exception as e:
        return {"error": str(e), "teams": [], "total_teams": 0}


@app.post("/workspaces/{workspace_name}/states/{state_abbr}/teams")
def create_team(workspace_name: str, state_abbr: str, team: dict, current_user: UserInDB = Depends(set_user_context)):
    """
    Create a new team for a workspace and state.
    
    If team_id is not provided, it will be auto-generated.
    """
    from planning_engine.team_management import add_team, generate_team_id
    from planning_engine.models import Team
    from datetime import date
    
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


@app.put("/workspaces/{workspace_name}/states/{state_abbr}/teams/{team_id}")
def update_team_endpoint(workspace_name: str, state_abbr: str, team_id: str, team: dict, current_user: UserInDB = Depends(set_user_context)):
    """
    Update an existing team.
    """
    from planning_engine.team_management import update_team
    from planning_engine.models import Team
    
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


@app.delete("/workspaces/{workspace_name}/states/{state_abbr}/teams/{team_id}")
def delete_team_endpoint(workspace_name: str, state_abbr: str, team_id: str, current_user: UserInDB = Depends(set_user_context)):
    """
    Delete a team.
    """
    from planning_engine.team_management import delete_team
    
    try:
        success = delete_team(workspace_name, state_abbr, team_id)
        
        if success:
            return {"success": True, "message": f"Team {team_id} deleted"}
        else:
            return {"success": False, "error": f"Team {team_id} not found"}
    
    except Exception as e:
        return {"success": False, "error": f"Failed to delete team: {str(e)}"}


@app.get("/workspaces/{workspace_name}/states/{state_abbr}/teams/generate-id")
def generate_team_id_endpoint(workspace_name: str, state_abbr: str, current_user: UserInDB = Depends(set_user_context)):
    """
    Generate a unique team ID for a state.
    
    Useful for UI to pre-populate team_id field.
    """
    from planning_engine.team_management import generate_team_id
    
    try:
        team_id = generate_team_id(workspace_name, state_abbr)
        return {"team_id": team_id}
    except Exception as e:
        return {"error": str(e)}


@app.get("/workspaces/{workspace_name}/states/{state_abbr}/cities")
def get_cities(workspace_name: str, state_abbr: str, current_user: UserInDB = Depends(set_user_context)):
    """
    Get list of available cities for a state from geocoded data.
    Used to populate city dropdown when creating teams.
    """
    from planning_engine.team_management import get_available_cities
    
    try:
        cities = get_available_cities(workspace_name, state_abbr)
        return {"cities": cities}
    except Exception as e:
        return {"error": str(e), "cities": []}


@app.get("/workspaces/{workspace_name}/states/{state_abbr}/planning-team-ids")
def get_planning_team_ids(workspace_name: str, state_abbr: str, current_user: UserInDB = Depends(set_user_context)):
    """
    Get unique Team IDs from the latest planning result for a state.
    Used to populate Team ID dropdown when creating teams.
    
    Returns list of unique team IDs from the most recent planning output.
    If no planning result exists, returns empty list.
    """
    from pathlib import Path
    import json
    from planning_engine.core.workspace import validate_workspace
    
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


# ============================================================================
# PROGRESS TRACKING ENDPOINTS
# ============================================================================

@app.get("/workspaces/{workspace_name}/progress")
def get_progress(workspace_name: str, state: str = None, current_user: UserInDB = Depends(set_user_context)):
    """
    Get progress tracking data for a workspace.
    
    Optional query parameter 'state' to filter by state abbreviation.
    If not provided, returns progress for all states.
    """
    from planning_engine.progress_tracking import load_progress
    
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


@app.post("/workspaces/{workspace_name}/progress/init")
def initialize_progress(workspace_name: str, force_refresh: bool = False, current_user: UserInDB = Depends(set_user_context)):
    """
    Initialize progress tracking from geocoded sites.
    
    Scans all cache/{state}/geocoded.csv files and creates progress.csv
    with 'pending' status for all sites.
    
    Query parameter 'force_refresh' will re-scan and add any new sites.
    """
    from planning_engine.progress_tracking import initialize_progress_from_geocoded
    
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


@app.put("/workspaces/{workspace_name}/progress/{site_id}")
def update_progress(workspace_name: str, site_id: str, update_data: dict, current_user: UserInDB = Depends(set_user_context)):
    """
    Update progress for a single site.
    
    Accepts partial updates - only provided fields will be updated.
    """
    from planning_engine.progress_tracking import update_site_progress
    
    try:
        # Extract update fields
        status = update_data.get('status')
        completed_date = update_data.get('completed_date')
        crew_assigned = update_data.get('crew_assigned')
        notes = update_data.get('notes')
        
        # Convert completed_date string to date if provided
        if completed_date:
            from datetime import datetime
            completed_date = datetime.fromisoformat(completed_date).date()
        
        updated_site = update_site_progress(
            workspace_name,
            site_id,
            status=status,
            completed_date=completed_date,
            crew_assigned=crew_assigned,
            notes=notes
        )
        
        return {"success": True, "site": updated_site}
    
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        return {"success": False, "error": f"Failed to update progress: {str(e)}"}


@app.put("/workspaces/{workspace_name}/progress/bulk")
def bulk_update_progress_endpoint(workspace_name: str, update_data: dict, current_user: UserInDB = Depends(set_user_context)):
    """
    Bulk update progress for multiple sites.
    
    Request body should include:
    - site_ids: List of site IDs to update
    - status: Optional new status
    - completed_date: Optional completion date
    - crew_assigned: Optional crew assignment
    - notes: Optional notes
    """
    from planning_engine.progress_tracking import bulk_update_progress
    
    try:
        site_ids = update_data.get('site_ids', [])
        status = update_data.get('status')
        completed_date = update_data.get('completed_date')
        crew_assigned = update_data.get('crew_assigned')
        notes = update_data.get('notes')
        
        # Convert completed_date string to date if provided
        if completed_date:
            from datetime import datetime
            completed_date = datetime.fromisoformat(completed_date).date()
        
        updated_count = bulk_update_progress(
            workspace_name,
            site_ids,
            status=status,
            completed_date=completed_date,
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

