"""Progress tracking functionality for site completion tracking.

Progress is stored in a workspace-wide CSV file at:
data/workspace/{workspace_name}/progress.csv

This module provides CRUD operations for progress tracking and
automatic initialization from geocoded sites.
"""

from pathlib import Path
from typing import List, Optional
import pandas as pd
from datetime import date, datetime

from .models import SiteProgress, ProgressResponse
from .core.workspace import validate_workspace


def get_progress_csv_path(workspace_name: str) -> Path:
    """Get the path to the progress.csv file for a workspace.
    
    Args:
        workspace_name: Name of the workspace
        
    Returns:
        Path to progress.csv file
    """
    workspace_path = validate_workspace(workspace_name)
    progress_csv = workspace_path / "progress.csv"
    
    return progress_csv


def initialize_progress_from_geocoded(workspace_name: str, force_refresh: bool = False) -> int:
    """Initialize progress.csv from all geocoded sites in the workspace.
    
    Scans all cache/{state}/geocoded.csv files and creates progress entries
    with 'pending' status for sites that don't already exist in progress.csv.
    
    Args:
        workspace_name: Name of the workspace
        force_refresh: If True, re-scan and add any new sites
        
    Returns:
        Number of sites added to progress tracking
    """
    workspace_path = validate_workspace(workspace_name)
    progress_csv = get_progress_csv_path(workspace_name)
    
    # Load existing progress if it exists
    existing_progress = {}
    if progress_csv.exists() and not force_refresh:
        try:
            df = pd.read_csv(progress_csv)
            existing_progress = {row['site_id']: row for _, row in df.iterrows()}
        except Exception as e:
            print(f"Warning: Could not load existing progress.csv: {e}")
    
    # Scan all state directories for geocoded.csv files
    cache_dir = workspace_path / "cache"
    if not cache_dir.exists():
        return 0
    
    new_sites = []
    current_time = datetime.now().isoformat()
    
    for state_dir in cache_dir.iterdir():
        if not state_dir.is_dir():
            continue
        
        state_abbr = state_dir.name
        geocoded_csv = state_dir / "geocoded.csv"
        
        if not geocoded_csv.exists():
            continue
        
        try:
            df_geocoded = pd.read_csv(geocoded_csv)
            
            # Try to load clustered.csv for cluster_id
            clustered_csv = state_dir / "clustered.csv"
            cluster_map = {}
            if clustered_csv.exists():
                try:
                    df_clustered = pd.read_csv(clustered_csv)
                    # Create mapping of site_id -> cluster_id
                    for _, row in df_clustered.iterrows():
                        sid = str(row.get('site_id', row.get('id', '')))
                        cid = row.get('cluster_id', row.get('cluster', None))
                        if sid and pd.notna(cid):
                            cluster_map[sid] = int(cid)
                except Exception as e:
                    print(f"Warning: Could not load clustered.csv for {state_abbr}: {e}")
            
            for _, row in df_geocoded.iterrows():
                site_id = str(row.get('site_id', row.get('id', '')))
                
                if not site_id:
                    continue
                
                # Skip if site already exists in progress
                if site_id in existing_progress:
                    continue
                
                # Extract city from geocoded data
                city = row.get('city', '')
                if pd.isna(city):
                    city = ''
                
                # Extract street1 from geocoded data
                street1 = row.get('street1', '')
                if pd.isna(street1):
                    street1 = ''
                
                # Get cluster_id from cluster_map if available
                cluster_id = cluster_map.get(site_id, None)
                
                # Create new progress entry
                new_sites.append({
                    'site_id': site_id,
                    'status': 'pending',
                    'completed_date': None,
                    'crew_assigned': None,
                    'notes': '',
                    'state': state_abbr,
                    'city': city,
                    'street1': street1,
                    'cluster_id': cluster_id,
                    'last_updated': current_time
                })
        
        except Exception as e:
            print(f"Warning: Could not process {geocoded_csv}: {e}")
            continue
    
    if not new_sites and not existing_progress:
        # No sites found at all
        return 0
    
    # Combine existing and new sites
    all_sites = list(existing_progress.values()) + new_sites
    
    # Save to progress.csv
    if all_sites:
        df = pd.DataFrame(all_sites)
        df.to_csv(progress_csv, index=False)
    
    return len(new_sites)


def load_progress(workspace_name: str, state_filter: Optional[str] = None) -> ProgressResponse:
    """Load progress data for a workspace, optionally filtered by state.
    
    Args:
        workspace_name: Name of the workspace
        state_filter: Optional state abbreviation to filter by (None = all states)
        
    Returns:
        ProgressResponse with progress records and statistics
    """
    progress_csv = get_progress_csv_path(workspace_name)
    
    if not progress_csv.exists():
        # No progress file yet - return empty response
        return ProgressResponse(
            progress=[],
            total_sites=0,
            by_status={}
        )
    
    try:
        df = pd.read_csv(progress_csv)
        
        if df.empty:
            return ProgressResponse(
                progress=[],
                total_sites=0,
                by_status={}
            )
        
        # Filter by state if specified
        if state_filter:
            df = df[df['state'] == state_filter]
        
        # Convert DataFrame to list of SiteProgress objects
        progress_list = []
        for _, row in df.iterrows():
            progress_data = row.to_dict()
            
            # Convert site_id to string (pandas may read it as int)
            if 'site_id' in progress_data:
                progress_data['site_id'] = str(progress_data['site_id'])
            
            # Handle date fields
            for date_field in ['completed_date']:
                if date_field in progress_data and pd.notna(progress_data[date_field]):
                    try:
                        progress_data[date_field] = pd.to_datetime(progress_data[date_field]).date()
                    except:
                        progress_data[date_field] = None
                else:
                    progress_data[date_field] = None
            
            # Handle optional string fields
            for field in ['crew_assigned', 'notes', 'last_updated', 'city', 'street1']:
                if field in progress_data and pd.isna(progress_data[field]):
                    progress_data[field] = "" if field in ['notes', 'city', 'street1'] else None
                elif field not in progress_data:
                    # For backward compatibility with old progress.csv files
                    progress_data[field] = "" if field in ['notes', 'city', 'street1'] else None
            
            # Handle cluster_id (convert to int or None)
            if 'cluster_id' in progress_data:
                if pd.isna(progress_data['cluster_id']):
                    progress_data['cluster_id'] = None
                else:
                    try:
                        progress_data['cluster_id'] = int(progress_data['cluster_id'])
                    except:
                        progress_data['cluster_id'] = None
            
            progress_list.append(SiteProgress(**progress_data))
        
        # Calculate statistics
        status_counts = df['status'].value_counts().to_dict()
        
        return ProgressResponse(
            progress=progress_list,
            total_sites=len(progress_list),
            by_status=status_counts
        )
    
    except Exception as e:
        raise ValueError(f"Failed to load progress from {progress_csv}: {str(e)}")


def save_progress(workspace_name: str, progress_list: List[SiteProgress]) -> Path:
    """Save progress data to CSV file, overwriting existing file.
    
    Args:
        workspace_name: Name of the workspace
        progress_list: List of SiteProgress objects to save
        
    Returns:
        Path to the saved progress.csv file
    """
    progress_csv = get_progress_csv_path(workspace_name)
    
    if not progress_list:
        # If no progress, create empty file with headers
        df = pd.DataFrame(columns=[
            'site_id', 'status', 'completed_date', 'crew_assigned',
            'notes', 'state', 'city', 'street1', 'cluster_id', 'last_updated'
        ])
    else:
        # Convert progress to DataFrame
        progress_dicts = [p.model_dump() for p in progress_list]
        df = pd.DataFrame(progress_dicts)
    
    # Save to CSV
    df.to_csv(progress_csv, index=False)
    
    return progress_csv


def update_site_progress(
    workspace_name: str,
    site_id: str,
    status: Optional[str] = None,
    completed_date: Optional[date] = None,
    crew_assigned: Optional[str] = None,
    notes: Optional[str] = None
) -> SiteProgress:
    """Update progress for a single site.
    
    Args:
        workspace_name: Name of the workspace
        site_id: ID of the site to update
        status: New status (if provided)
        completed_date: Completion date (if provided)
        crew_assigned: Assigned crew/team (if provided)
        notes: Notes (if provided)
        
    Returns:
        Updated SiteProgress object
        
    Raises:
        ValueError: If site_id not found
    """
    response = load_progress(workspace_name)
    progress_list = response.progress
    
    # Find the site
    site_index = None
    for i, site in enumerate(progress_list):
        if site.site_id == site_id:
            site_index = i
            break
    
    if site_index is None:
        raise ValueError(f"Site '{site_id}' not found in progress tracking")
    
    # Update fields
    site = progress_list[site_index]
    if status is not None:
        site.status = status
    if completed_date is not None:
        site.completed_date = completed_date
    if crew_assigned is not None:
        site.crew_assigned = crew_assigned
    if notes is not None:
        site.notes = notes
    
    # Update timestamp
    site.last_updated = datetime.now().isoformat()
    
    # Save changes
    save_progress(workspace_name, progress_list)
    
    return site


def bulk_update_progress(
    workspace_name: str,
    site_ids: List[str],
    status: Optional[str] = None,
    completed_date: Optional[date] = None,
    crew_assigned: Optional[str] = None,
    notes: Optional[str] = None
) -> int:
    """Bulk update progress for multiple sites.
    
    Args:
        workspace_name: Name of the workspace
        site_ids: List of site IDs to update
        status: New status (if provided)
        completed_date: Completion date (if provided)
        crew_assigned: Assigned crew/team (if provided)
        notes: Notes (if provided)
        
    Returns:
        Number of sites updated
    """
    response = load_progress(workspace_name)
    progress_list = response.progress
    
    current_time = datetime.now().isoformat()
    updated_count = 0
    
    # Update matching sites
    for site in progress_list:
        if site.site_id in site_ids:
            if status is not None:
                site.status = status
            if completed_date is not None:
                site.completed_date = completed_date
            if crew_assigned is not None:
                site.crew_assigned = crew_assigned
            if notes is not None:
                site.notes = notes
            
            site.last_updated = current_time
            updated_count += 1
    
    # Save changes
    save_progress(workspace_name, progress_list)
    
    return updated_count


def sync_progress_with_plan_result(workspace_name: str, plan_result: dict) -> int:
    """Sync progress.csv with planning results to auto-populate crew assignments.
    
    Called automatically after a planning run to update crew_assigned field
    based on which team was assigned to each site in the plan.
    
    Args:
        workspace_name: Name of the workspace
        plan_result: Planning result dictionary with team_days
        
    Returns:
        Number of sites updated with crew assignments
    """
    response = load_progress(workspace_name)
    progress_list = response.progress
    
    # Build mapping of site_id -> crew_assigned from plan result
    site_to_crew = {}
    
    team_days = plan_result.get('team_days', [])
    for team_day in team_days:
        crew_label = team_day.get('team_label') or f"Team-{team_day.get('team_id', 'Unknown')}"
        site_ids = team_day.get('site_ids', [])
        
        for site_id in site_ids:
            site_to_crew[site_id] = crew_label
    
    if not site_to_crew:
        return 0
    
    # Update progress with crew assignments
    current_time = datetime.now().isoformat()
    updated_count = 0
    
    for site in progress_list:
        if site.site_id in site_to_crew:
            site.crew_assigned = site_to_crew[site.site_id]
            site.last_updated = current_time
            updated_count += 1
    
    # Save changes
    if updated_count > 0:
        save_progress(workspace_name, progress_list)
    
    return updated_count
