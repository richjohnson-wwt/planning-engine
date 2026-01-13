"""
Geocoding, Error Management, and Site Editor API Router
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import pandas as pd
import logging

from planning_engine import geocode
from planning_engine.paths import get_project_root, get_workspace_path

# Import authentication utilities
try:
    from ..auth import UserInDB, get_current_user
except ImportError:
    from auth import UserInDB, get_current_user

# Import context management for user-scoped workspaces
from planning_engine.paths import set_current_username

router = APIRouter(tags=["geocoding"])


# Dependency to set username context for all authenticated requests
async def set_user_context(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """Set the username context for user-scoped workspace paths."""
    set_current_username(current_user.username)
    return current_user


# ============================================================================
# Models
# ============================================================================

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


# ============================================================================
# Geocoding Endpoints
# ============================================================================

@router.post("/geocode", response_model=GeocodeResponse)
def geocode_addresses(request: GeocodeRequest, current_user: UserInDB = Depends(set_user_context)):
    """Geocode addresses from workspace's state-specific addresses.csv file"""
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

@router.get("/workspaces/{workspace_name}/geocode-errors/{state_abbr}")
def get_geocode_errors(
    workspace_name: str, 
    state_abbr: str, 
    current_user: UserInDB = Depends(set_user_context)
):
    """
    Get list of geocoding errors for a specific state.
    
    Returns all addresses that failed geocoding from the geocoded-errors.csv file.
    """
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


@router.post("/workspaces/{workspace_name}/geocode-errors/{state_abbr}/retry")
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


@router.delete("/workspaces/{workspace_name}/geocode-errors/{state_abbr}/{site_id}")
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

@router.get("/workspaces/{workspace_name}/geocoded/{state_abbr}/{site_id}")
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


@router.put("/workspaces/{workspace_name}/geocoded/{state_abbr}/{site_id}")
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
