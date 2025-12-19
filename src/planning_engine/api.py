from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta
from .models import PlanRequest, PlanResult, TeamDay, Site


def _load_sites_from_workspace(workspace_name: str, state_abbr: Optional[str] = None) -> List[Site]:
    """
    Load sites from workspace's geocoded.csv file.
    
    Args:
        workspace_name: Name of the workspace
        state_abbr: Optional state abbreviation to filter sites (e.g., "LA", "NC")
        
    Returns:
        List of Site objects
        
    Raises:
        FileNotFoundError: If workspace or geocoded.csv doesn't exist
    """
    import pandas as pd
    
    # Validate workspace exists
    workspace_path = Path("data") / "workspace" / workspace_name
    if not workspace_path.exists():
        raise FileNotFoundError(
            f"Workspace '{workspace_name}' does not exist. "
            f"Create it first using new_workspace('{workspace_name}')"
        )
    
    # Check if geocoded.csv exists
    geocoded_csv = workspace_path / "cache" / "geocoded.csv"
    if not geocoded_csv.exists():
        raise FileNotFoundError(
            f"geocoded.csv not found in workspace '{workspace_name}'. "
            f"Run geocode() first to create geocoded.csv"
        )
    
    # Read geocoded data
    df = pd.read_csv(geocoded_csv)
    
    # Filter by state if provided
    if state_abbr:
        df = df[df['state'] == state_abbr.upper()]
        if len(df) == 0:
            raise ValueError(
                f"No sites found for state '{state_abbr}' in workspace '{workspace_name}'"
            )
    
    # Convert to Site objects
    sites = []
    for _, row in df.iterrows():
        site = Site(
            id=str(row['site_id']),
            name=f"{row['city']} - {row['street1']}",
            lat=float(row['lat']),
            lon=float(row['lon']),
            service_minutes=60  # Default service time
        )
        sites.append(site)
    
    return sites


def plan(request: PlanRequest) -> PlanResult:
    """
    Plan routes for teams/crews to visit sites.
    
    If OR-Tools specific fields (start_date, end_date) are provided, uses OR-Tools solver
    for optimized multi-day VRPTW routing. Otherwise, uses simple assignment.
    
    Sites can be provided explicitly or auto-loaded from geocoded.csv filtered by state_abbr.
    """
    # Load sites from geocoded.csv if not provided
    if request.sites is None:
        request.sites = _load_sites_from_workspace(request.workspace, request.state_abbr)
    
    # Validate we have sites to plan
    if not request.sites:
        raise ValueError(
            f"No sites found for workspace '{request.workspace}'"
            + (f" with state '{request.state_abbr}'" if request.state_abbr else "")
        )
    
    # Check if OR-Tools solver should be used
    if request.start_date and request.end_date:
        return _plan_with_ortools(request)
    else:
        # Simple fallback: assign all sites to team 1
        total_service = sum(s.service_minutes for s in request.sites)
        team_days = [
            TeamDay(
                team_id=1,
                site_ids=[s.id for s in request.sites],
                service_minutes=total_service,
                route_minutes=total_service,  # No travel time in simple mode
            )
        ]
        return PlanResult(team_days=team_days)


def _plan_with_ortools(request: PlanRequest) -> PlanResult:
    """Use OR-Tools solver for optimized routing."""
    from .ortools_solver import plan_routes
    
    return plan_routes(request)


def new_workspace(workspace_name: str) -> Path:
    if not workspace_name or not workspace_name.strip():
        raise ValueError("Workspace name cannot be empty")
    
    # Sanitize workspace name to prevent path traversal
    safe_name = "".join(c for c in workspace_name if c.isalnum() or c in ("-", "_", " ")).strip()
    if not safe_name:
        raise ValueError(f"Invalid workspace name: {workspace_name}")
    
    # Create workspace directory under /data/workspace
    workspace_path = Path("data") / "workspace" / safe_name
    workspace_path.mkdir(parents=True, exist_ok=True)
    
    # Create subdirectories for organizing workflow data
    (workspace_path / "input").mkdir(exist_ok=True)
    (workspace_path / "output").mkdir(exist_ok=True)
    (workspace_path / "cache").mkdir(exist_ok=True)
    
    return workspace_path


def parse_excel(
    workspace_name: str,
    file_path: str,
    column_mapping: dict[str, str]
) -> Path:
    """
    Parse an Excel file and save mapped columns to the workspace.
    
    Maps client-specific Excel column names to standardized field names.
    Required fields: site_id, street1, city, state, zip
    Optional fields: street2
    
    Args:
        workspace_name: Name of the workspace where output will be saved
        file_path: Path to the Excel file to parse
        column_mapping: Dict mapping standard field names to Excel column names.
                       Format: {standard_name: excel_column_name}
                       Example: {"site_id": "Location", "street1": "MyStreet1",
                                "city": "MyCity", "state": "MyState", "zip": "MyZip"}
                       Optional: {"street2": "MyStreet2"}
        
    Returns:
        Path to the created addresses.csv file
        
    Raises:
        FileNotFoundError: If the Excel file or workspace doesn't exist
        ValueError: If mapped columns don't exist in the Excel file or required fields are missing
    """
    from .data_prep.parse_xlsx import parse_excel_to_csv
    
    # Validate required fields are in the mapping
    # street2 is optional since not all clients have a secondary address line
    required_fields = {'site_id', 'street1', 'city', 'state', 'zip'}
    optional_fields = {'street2'}
    provided_fields = set(column_mapping.keys())
    missing_fields = required_fields - provided_fields
    
    if missing_fields:
        raise ValueError(
            f"Missing required fields in column_mapping: {', '.join(missing_fields)}. "
            f"Required fields: {', '.join(sorted(required_fields))}. "
            f"Optional fields: {', '.join(sorted(optional_fields))}"
        )
    
    # Validate workspace exists
    workspace_path = Path("data") / "workspace" / workspace_name
    if not workspace_path.exists():
        raise FileNotFoundError(
            f"Workspace '{workspace_name}' does not exist. "
            f"Create it first using new_workspace('{workspace_name}')"
        )
    
    # Validate Excel file exists
    excel_file = Path(file_path)
    if not excel_file.exists():
        raise FileNotFoundError(f"Excel file not found: {file_path}")
    
    # Define output path
    output_path = workspace_path / "input" / "addresses.csv"
    
    # Parse Excel and save to CSV
    result_path = parse_excel_to_csv(
        file_path=str(excel_file),
        output_path=str(output_path),
        column_mapping=column_mapping
    )
    
    return result_path

def geocode(workspace_name: str) -> Path:
    """
    Geocode addresses from the workspace's addresses.csv file.
    
    Reads addresses from data/workspace/{workspace_name}/input/addresses.csv,
    calls the batch geocoding API, and saves results to 
    data/workspace/{workspace_name}/cache/geocoded.csv.
    
    Args:
        workspace_name: Name of the workspace containing addresses.csv
        
    Returns:
        Path to the created geocoded.csv file
        
    Raises:
        FileNotFoundError: If workspace or addresses.csv doesn't exist
        Exception: If geocoding fails
    """
    import pandas as pd
    from .data_prep.geocode import batch_geocode_sites
    
    # Validate workspace exists
    workspace_path = Path("data") / "workspace" / workspace_name
    if not workspace_path.exists():
        raise FileNotFoundError(
            f"Workspace '{workspace_name}' does not exist. "
            f"Create it first using new_workspace('{workspace_name}')"
        )
    
    # Check if addresses.csv exists
    addresses_csv = workspace_path / "input" / "addresses.csv"
    if not addresses_csv.exists():
        raise FileNotFoundError(
            f"addresses.csv not found in workspace '{workspace_name}'. "
            f"Run parse_excel() first to create addresses.csv"
        )
    
    # Read addresses from CSV
    df = pd.read_csv(addresses_csv)
    
    # Build full address strings for geocoding
    # Format: "street1, street2, city, state zip"
    addresses = []
    for _, row in df.iterrows():
        parts = [str(row['street1'])]
        if 'street2' in df.columns and pd.notna(row.get('street2')) and str(row.get('street2')).strip():
            parts.append(str(row['street2']))
        parts.append(f"{row['city']}, {row['state']} {row['zip']}")
        address = ", ".join(parts)
        addresses.append(address)
    
    print(f"Geocoding {len(addresses)} addresses from {addresses_csv}...")
    
    # Call batch geocoding API
    geocode_results = batch_geocode_sites(addresses)
    
    # Parse results and add lat/lon to dataframe
    # Assuming geocodify returns results with 'lat' and 'lon' fields
    lats = []
    lons = []
    for result in geocode_results:
        if result and 'lat' in result and 'lon' in result:
            lats.append(result['lat'])
            lons.append(result['lon'])
        else:
            # Handle failed geocoding for individual addresses
            lats.append(None)
            lons.append(None)
    
    df['lat'] = lats
    df['lon'] = lons
    
    # Save to cache directory
    output_path = workspace_path / "cache" / "geocoded.csv"
    df.to_csv(output_path, index=False)
    
    print(f"✓ Geocoded addresses saved to: {output_path}")
    
    return output_path


def cluster(workspace_name: str) -> Path:
    """
    Cluster geocoded sites based on their geographic coordinates.
    
    Uses automatic k-means clustering with optimal cluster count determined
    by silhouette score analysis. Reads from cache/geocoded.csv and saves
    results to cache/clustered.csv.
    
    Args:
        workspace_name: Name of the workspace containing geocoded.csv
        
    Returns:
        Path to the created clustered.csv file
        
    Raises:
        FileNotFoundError: If workspace or geocoded.csv doesn't exist
        ValueError: If geocoded.csv has invalid data
    """
    import pandas as pd
    from .data_prep.cluster import cluster_sites
    
    # Validate workspace exists
    workspace_path = Path("data") / "workspace" / workspace_name
    if not workspace_path.exists():
        raise FileNotFoundError(
            f"Workspace '{workspace_name}' does not exist. "
            f"Create it first using new_workspace('{workspace_name}')"
        )
    
    # Check if geocoded.csv exists
    geocoded_csv = workspace_path / "cache" / "geocoded.csv"
    if not geocoded_csv.exists():
        raise FileNotFoundError(
            f"geocoded.csv not found in workspace '{workspace_name}'. "
            f"Run geocode() first to create geocoded.csv"
        )
    
    # Read geocoded data
    df = pd.read_csv(geocoded_csv)
    print(f"Clustering {len(df)} sites from {geocoded_csv}...")
    
    # Perform clustering
    df_clustered = cluster_sites(df)
    
    # Save to cache directory
    output_path = workspace_path / "cache" / "clustered.csv"
    df_clustered.to_csv(output_path, index=False)
    
    print(f"✓ Clustered sites saved to: {output_path}")
    
    return output_path