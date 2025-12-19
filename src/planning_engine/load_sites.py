"""Helper functions to load sites from workspace CSV files."""

from pathlib import Path
from typing import List
import pandas as pd
from .models import Site


def load_sites_from_workspace(
    workspace_name: str, 
    use_clustered: bool = False,
    cluster_id: int = None
) -> List[Site]:
    """
    Load sites from workspace geocoded.csv or clustered.csv.
    
    This integrates with the pipeline workflow:
    parse_excel → geocode → [optional: cluster] → load_sites → plan
    
    Args:
        workspace_name: Name of the workspace
        use_clustered: If True, loads from clustered.csv, otherwise from geocoded.csv
        cluster_id: Optional cluster ID to filter sites (only used when use_clustered=True)
        
    Returns:
        List of Site objects with id, name, lat, lon, and service_minutes
        
    Raises:
        FileNotFoundError: If workspace or CSV file doesn't exist
        ValueError: If CSV is missing required columns
        
    Example:
        >>> from planning_engine import load_sites_from_workspace, plan
        >>> from planning_engine.models import PlanRequest, TeamConfig, Workday
        >>> from datetime import time, date
        >>> 
        >>> # Load sites from geocoded.csv
        >>> sites = load_sites_from_workspace("my_workspace")
        >>> 
        >>> # Create plan request
        >>> req = PlanRequest(
        ...     workspace="my_workspace",
        ...     sites=sites,
        ...     team_config=TeamConfig(teams=2, workday=Workday(...)),
        ...     start_date=date(2025, 1, 1),
        ...     end_date=date(2025, 1, 5)
        ... )
        >>> 
        >>> # Run planning
        >>> result = plan(req)
    """
    # Validate workspace exists
    workspace_path = Path("data") / "workspace" / workspace_name
    if not workspace_path.exists():
        raise FileNotFoundError(
            f"Workspace '{workspace_name}' does not exist. "
            f"Create it first using new_workspace('{workspace_name}')"
        )
    
    # Determine which CSV to load
    if use_clustered:
        csv_path = workspace_path / "cache" / "clustered.csv"
        if not csv_path.exists():
            raise FileNotFoundError(
                f"clustered.csv not found in workspace '{workspace_name}'. "
                f"Run cluster() first to create clustered.csv"
            )
    else:
        csv_path = workspace_path / "cache" / "geocoded.csv"
        if not csv_path.exists():
            raise FileNotFoundError(
                f"geocoded.csv not found in workspace '{workspace_name}'. "
                f"Run geocode() first to create geocoded.csv"
            )
    
    # Read CSV
    df = pd.read_csv(csv_path)
    
    # Filter by cluster if specified
    if cluster_id is not None and use_clustered:
        if 'cluster_id' not in df.columns:
            raise ValueError(
                f"clustered.csv is missing 'cluster_id' column. "
                f"Found columns: {', '.join(df.columns)}"
            )
        df = df[df['cluster_id'] == cluster_id]
        print(f"  Filtering to cluster {cluster_id}: {len(df)} sites")
    
    # Validate required columns
    required_cols = ['site_id', 'lat', 'lon']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(
            f"CSV is missing required columns: {', '.join(missing_cols)}. "
            f"Found columns: {', '.join(df.columns)}"
        )
    
    # Build Site objects
    sites = []
    for idx, row in df.iterrows():
        # Use site_id as both id and name (or use street1 if available)
        site_id = str(row['site_id'])
        
        # Try to build a readable name from address fields
        if 'street1' in df.columns and pd.notna(row.get('street1')):
            name = str(row['street1'])
        else:
            name = site_id
        
        # Get service minutes (default to 60 if not specified)
        service_minutes = 60
        if 'service_minutes' in df.columns and pd.notna(row.get('service_minutes')):
            service_minutes = int(row['service_minutes'])
        
        # Skip sites with missing lat/lon
        if pd.isna(row['lat']) or pd.isna(row['lon']):
            print(f"Warning: Skipping site {site_id} - missing coordinates")
            continue
        
        site = Site(
            id=site_id,
            name=name,
            lat=float(row['lat']),
            lon=float(row['lon']),
            service_minutes=service_minutes
        )
        sites.append(site)
    
    print(f"✓ Loaded {len(sites)} sites from {csv_path}")
    return sites
