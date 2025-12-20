from pathlib import Path
from typing import List, Optional
from .models import PlanRequest, PlanResult, TeamDay, Site, CalendarPlanResult
from .calendar_wrapper import plan_fixed_calendar, plan_fixed_crews


def _load_sites_from_workspace(workspace_name: str, state_abbr: Optional[str] = None) -> List[Site]:
    """
    Load sites from workspace's state-specific geocoded.csv file.
    
    Args:
        workspace_name: Name of the workspace
        state_abbr: State abbreviation to load sites for (e.g., "LA", "NC"). Required.
        
    Returns:
        List of Site objects
        
    Raises:
        FileNotFoundError: If workspace or geocoded.csv doesn't exist
        ValueError: If state_abbr is not provided
    """
    import pandas as pd
    
    # Validate state_abbr is provided
    if not state_abbr:
        raise ValueError(
            "state_abbr is required to load sites. "
            "Specify which state's sites to load (e.g., 'LA', 'NC')"
        )
    
    # Validate workspace exists
    workspace_path = Path("data") / "workspace" / workspace_name
    if not workspace_path.exists():
        raise FileNotFoundError(
            f"Workspace '{workspace_name}' does not exist. "
            f"Create it first using new_workspace('{workspace_name}')"
        )
    
    # Check if state-specific geocoded.csv exists
    geocoded_csv = workspace_path / "cache" / state_abbr / "geocoded.csv"
    if not geocoded_csv.exists():
        raise FileNotFoundError(
            f"geocoded.csv not found for state '{state_abbr}' in workspace '{workspace_name}'. "
            f"Expected path: {geocoded_csv}. Run geocode() first to create geocoded.csv"
        )
    
    # Read geocoded data
    df = pd.read_csv(geocoded_csv)
    
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
    If use_clusters is True, loads from clustered.csv and plans each cluster separately.
    """
    # Handle cluster-based planning
    if request.use_clusters:
        return _plan_with_clusters(request)
    
    # Load sites from geocoded.csv if not provided
    if request.sites is None:
        request.sites = _load_sites_from_workspace(request.workspace, request.state_abbr)
    
    # Validate we have sites to plan
    if not request.sites:
        raise ValueError(
            f"No sites found for workspace '{request.workspace}'"
            + (f" with state '{request.state_abbr}'" if request.state_abbr else "")
        )
    
    # Check if calendar-based planning should be used
    if request.start_date and request.end_date:
        # Fixed calendar mode: optimize crews for date range
        calendar_result = plan_fixed_calendar(request)
        return calendar_result.to_plan_result()
    elif request.num_crews_available is not None:
        # Fixed crews mode: optimize days for given crews
        calendar_result = plan_fixed_crews(request)
        return calendar_result.to_plan_result()
    else:
        # Simple fallback: assign all sites to team 1 (no optimization)
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


def _plan_with_clusters(request: PlanRequest) -> PlanResult:
    """
    Plan routes using cluster-based approach.
    
    Loads sites from clustered.csv, groups by cluster_id, plans each cluster separately,
    and combines the results. This prevents geographic constraint issues by keeping
    routes within cluster boundaries.
    """
    import pandas as pd
    
    # Validate state_abbr is provided
    if not request.state_abbr:
        raise ValueError(
            "state_abbr is required when use_clusters is True. "
            "Specify which state's clusters to load (e.g., 'LA', 'NC')"
        )
    
    # Validate workspace exists
    workspace_path = Path("data") / "workspace" / request.workspace
    if not workspace_path.exists():
        raise FileNotFoundError(
            f"Workspace '{request.workspace}' does not exist. "
            f"Create it first using new_workspace('{request.workspace}')"
        )
    
    # Check if state-specific clustered.csv exists
    clustered_csv = workspace_path / "cache" / request.state_abbr / "clustered.csv"
    if not clustered_csv.exists():
        raise FileNotFoundError(
            f"clustered.csv not found for state '{request.state_abbr}' in workspace '{request.workspace}'. "
            f"Expected path: {clustered_csv}. Run cluster() first to create clustered.csv"
        )
    
    # Read clustered data
    df = pd.read_csv(clustered_csv)
    
    # Get unique cluster IDs (convert to Python int to avoid numpy serialization issues)
    cluster_ids = sorted([int(cid) for cid in df['cluster_id'].unique()])
    print(f"Planning {len(cluster_ids)} clusters for state '{request.state_abbr}'...")
    
    all_team_days = []
    
    # Plan each cluster separately
    for cluster_id in cluster_ids:
        # Filter sites for this cluster
        cluster_df = df[df['cluster_id'] == cluster_id]
        
        # Convert to Site objects
        cluster_sites = []
        for _, row in cluster_df.iterrows():
            site = Site(
                id=str(row['site_id']),
                name=f"{row['city']} - {row['street1']}",
                lat=float(row['lat']),
                lon=float(row['lon']),
                service_minutes=request.service_minutes_per_site
            )
            cluster_sites.append(site)
        
        print(f"  Cluster {cluster_id}: {len(cluster_sites)} sites")
        
        # Create a new request for this cluster
        cluster_request = PlanRequest(
            workspace=request.workspace,
            sites=cluster_sites,
            team_config=request.team_config,
            state_abbr=request.state_abbr,
            use_clusters=False,  # Prevent recursion
            start_date=request.start_date,
            end_date=request.end_date,
            num_crews_available=request.num_crews_available,
            max_route_minutes=request.max_route_minutes,
            break_minutes=request.break_minutes,
            holidays=request.holidays,
            service_minutes_per_site=request.service_minutes_per_site,
            minimize_crews=request.minimize_crews
        )
        
        # Plan this cluster using calendar-based multi-day planning
        if cluster_request.start_date and cluster_request.end_date:
            cluster_calendar_result = plan_fixed_calendar(cluster_request)
            cluster_result = cluster_calendar_result.to_plan_result()
        else:
            cluster_calendar_result = plan_fixed_crews(cluster_request)
            cluster_result = cluster_calendar_result.to_plan_result()
        
        # Adjust team IDs to be unique across clusters
        # Cluster 0: teams 1-9, Cluster 1: teams 10-19, etc.
        for td in cluster_result.team_days:
            td.team_id = td.team_id + (cluster_id * 100)
        
        all_team_days.extend(cluster_result.team_days)
        print(f"    ✓ Cluster {cluster_id}: {len(cluster_result.team_days)} team-days scheduled")
    
    # Combine results from all clusters
    print(f"✓ Total: {len(all_team_days)} team-days across {len(cluster_ids)} clusters")
    return PlanResult(team_days=all_team_days, unassigned=0)


def _plan_with_ortools(request: PlanRequest) -> PlanResult:
    """Use OR-Tools single-day VRP solver for optimized routing."""
    from .ortools_solver import plan_single_day_vrp
    
    return plan_single_day_vrp(request)


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
) -> dict[str, Path]:
    """
    Parse an Excel file and save mapped columns to the workspace, organized by state.
    
    Maps client-specific Excel column names to standardized field names.
    Sites are grouped by state and saved to separate folders:
    - data/workspace/{workspace}/input/{STATE}/addresses.csv
    
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
        Dict mapping state names to their addresses.csv file paths
        Example: {"LA": Path("data/workspace/foobar/input/LA/addresses.csv"), ...}
        
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
    
    # Define output path (base path - states will be organized under input/)
    output_path = workspace_path / "input" / "addresses.csv"
    
    # Parse Excel and save to CSV files organized by state
    print(f"Parsing Excel file and organizing by state...")
    state_files = parse_excel_to_csv(
        file_path=str(excel_file),
        output_path=str(output_path),
        column_mapping=column_mapping
    )
    
    print(f"✓ Parsed {len(state_files)} states: {', '.join(state_files.keys())}")
    
    return state_files

def geocode(workspace_name: str, state_abbr: str) -> Path:
    """
    Geocode addresses from the workspace's state-specific addresses.csv file.
    
    Reads addresses from data/workspace/{workspace_name}/input/{state_abbr}/addresses.csv,
    calls the batch geocoding API, and saves results to 
    data/workspace/{workspace_name}/cache/{state_abbr}/geocoded.csv.
    
    Args:
        workspace_name: Name of the workspace containing addresses.csv
        state_abbr: State abbreviation (e.g., "LA", "NC")
        
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
    
    # Check if state-specific addresses.csv exists
    addresses_csv = workspace_path / "input" / state_abbr / "addresses.csv"
    if not addresses_csv.exists():
        raise FileNotFoundError(
            f"addresses.csv not found for state '{state_abbr}' in workspace '{workspace_name}'. "
            f"Expected path: {addresses_csv}. Run parse_excel() first to create addresses.csv"
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
    
    print(f"Geocoding {len(addresses)} addresses for state '{state_abbr}' from {addresses_csv}...")
    
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
    
    # Save to state-specific cache directory
    cache_dir = workspace_path / "cache" / state_abbr
    cache_dir.mkdir(parents=True, exist_ok=True)
    output_path = cache_dir / "geocoded.csv"
    df.to_csv(output_path, index=False)
    
    print(f"✓ Geocoded addresses for state '{state_abbr}' saved to: {output_path}")
    
    return output_path


def cluster(workspace_name: str, state_abbr: str) -> Path:
    """
    Cluster geocoded sites based on their geographic coordinates.
    
    Uses automatic k-means clustering with optimal cluster count determined
    by silhouette score analysis. Reads from cache/{state_abbr}/geocoded.csv and saves
    results to cache/{state_abbr}/clustered.csv.
    
    Args:
        workspace_name: Name of the workspace containing geocoded.csv
        state_abbr: State abbreviation (e.g., "LA", "NC")
        
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
    
    # Check if state-specific geocoded.csv exists
    geocoded_csv = workspace_path / "cache" / state_abbr / "geocoded.csv"
    if not geocoded_csv.exists():
        raise FileNotFoundError(
            f"geocoded.csv not found for state '{state_abbr}' in workspace '{workspace_name}'. "
            f"Expected path: {geocoded_csv}. Run geocode() first to create geocoded.csv"
        )
    
    # Read geocoded data
    df = pd.read_csv(geocoded_csv)
    print(f"Clustering {len(df)} sites for state '{state_abbr}' from {geocoded_csv}...")
    
    # Perform clustering
    df_clustered = cluster_sites(df)
    
    # Save to state-specific cache directory
    output_path = workspace_path / "cache" / state_abbr / "clustered.csv"
    df_clustered.to_csv(output_path, index=False)
    
    print(f"✓ Clustered sites for state '{state_abbr}' saved to: {output_path}")
    
    return output_path