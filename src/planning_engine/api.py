"""Public API for the planning engine.

This module provides the main interface for:
- Workspace management
- Data pipeline (parse Excel → geocode → cluster)
- Route planning
"""

from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd

from .models import PlanRequest, PlanResult
from .paths import get_workspace_path
from .planning.planner import execute_plan
from .cluster_validation import (
    get_cluster_info,
    validate_cluster_crew_allocation,
    get_cluster_recommendation_message
)


def new_workspace(workspace_name: str) -> Path:
    """
    Create a new workspace directory structure.
    
    Creates:
    - data/workspace/{workspace_name}/input/{STATE}/ - for addresses.csv files
    - data/workspace/{workspace_name}/cache/{STATE}/ - for geocoded/clustered files
    - data/workspace/{workspace_name}/output/{STATE}/ - for route plans
    
    Args:
        workspace_name: Name of the workspace to create
        
    Returns:
        Path to the created workspace directory
    """
    workspace_path = get_workspace_path(workspace_name)
    
    # Create directory structure (state-specific dirs created as needed)
    workspace_path.mkdir(parents=True, exist_ok=True)
    (workspace_path / "input").mkdir(exist_ok=True)
    (workspace_path / "cache").mkdir(exist_ok=True)
    (workspace_path / "output").mkdir(exist_ok=True)
    
    print(f"✓ Created workspace: {workspace_path}")
    return workspace_path


def parse_excel(
    workspace_name: str,
    file_path: str,
    column_mapping: dict[str, str],
    sheet_name: Optional[str] = None
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
        sheet_name: Name of the Excel sheet to parse. If None, uses the first sheet.
        
    Returns:
        Dict mapping state names to their addresses.csv file paths
        Example: {"LA": Path("data/workspace/foobar/input/LA/addresses.csv"), ...}
        
    Raises:
        FileNotFoundError: If the Excel file or workspace doesn't exist
        ValueError: If mapped columns don't exist in the Excel file or required fields are missing
    """
    from .data_prep.parse_xlsx import parse_excel_to_csv
    
    # Validate required fields
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
    workspace_path = get_workspace_path(workspace_name)
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
    
    # Parse Excel and save to CSV files organized by state
    print(f"Parsing Excel file and organizing by state...")
    state_files = parse_excel_to_csv(
        file_path=str(excel_file),
        output_path=str(output_path),
        column_mapping=column_mapping,
        sheet_name=sheet_name
    )
    
    print(f"✓ Parsed {len(state_files)} states: {', '.join(state_files.keys())}")
    
    return state_files


def geocode(workspace_name: str, state_abbr: str) -> Path:
    """
    Geocode addresses from the workspace's state-specific addresses.csv file.
    
    Reads addresses from data/workspace/{workspace_name}/input/{state_abbr}/addresses.csv,
    calls the batch geocoding API, and saves results to:
    - Successfully geocoded addresses: cache/{state_abbr}/geocoded.csv
    - Failed geocodes: cache/{state_abbr}/geocoded-errors.csv
    
    Args:
        workspace_name: Name of the workspace containing addresses.csv
        state_abbr: State abbreviation (e.g., "LA", "NC")
        
    Returns:
        Path to the created geocoded.csv file
        
    Raises:
        FileNotFoundError: If workspace or addresses.csv doesn't exist
        Exception: If geocoding fails
        ValueError: If geocoding errors occurred (with details in error message)
    """
    from .data_prep.geocode import batch_geocode_sites
    from .core.workspace import validate_workspace, validate_state_file
    
    # Validate workspace and addresses file
    workspace_path = validate_workspace(workspace_name)
    addresses_csv = validate_state_file(workspace_path, state_abbr, "addresses.csv", "addresses.csv")
    
    # Read addresses from CSV
    df = pd.read_csv(addresses_csv)
    
    # Helper function to normalize address components for better geocoding
    def normalize_address_component(text):
        """
        Normalize address text to improve geocoding success.
        
        Common issues:
        - Apostrophes and backticks in city names (e.g., O'Fallon, O`Fallon)
        - Smart quotes vs straight quotes
        - Multiple spaces
        """
        if pd.isna(text):
            return text
        
        text = str(text)
        
        # Replace apostrophes and backticks with spaces
        # Examples: O'Fallon → O Fallon, O`Fallon → O Fallon
        text = text.replace("'", " ")
        text = text.replace("`", " ")
        text = text.replace("'", " ")  # Smart apostrophe
        text = text.replace("'", " ")  # Another smart apostrophe variant
        
        # Normalize multiple spaces to single space
        text = " ".join(text.split())
        
        return text
    
    # Build full address strings for geocoding with normalization
    addresses = []
    for _, row in df.iterrows():
        # Normalize street addresses and city names
        street1 = normalize_address_component(row['street1'])
        parts = [street1]
        
        if 'street2' in df.columns and pd.notna(row.get('street2')) and str(row.get('street2')).strip():
            street2 = normalize_address_component(row['street2'])
            parts.append(street2)
        
        city = normalize_address_component(row['city'])
        
        # Format ZIP code - convert float to int string if needed
        zip_code = row['zip']
        if pd.notna(zip_code):
            # Convert to string, removing .0 if it's a float
            zip_str = str(zip_code)
            if '.' in zip_str:
                try:
                    zip_str = str(int(float(zip_str)))
                except (ValueError, TypeError):
                    pass  # Keep original if conversion fails
        else:
            zip_str = ''
        
        parts.append(f"{city}, {row['state']} {zip_str}")
        address = ", ".join(parts)
        addresses.append(address)
    
    print(f"Geocoding {len(addresses)} addresses for state '{state_abbr}' from {addresses_csv}...")
    
    # Call batch geocoding API
    geocode_results = batch_geocode_sites(addresses)
    
    # Parse results and add lat/lon to dataframe
    lats = []
    lons = []
    for result in geocode_results:
        if result and 'lat' in result and 'lon' in result:
            lats.append(result['lat'])
            lons.append(result['lon'])
        else:
            lats.append(None)
            lons.append(None)
    
    df['lat'] = lats
    df['lon'] = lons
    
    # Separate successful geocodes from failures
    df_success = df[df['lat'].notna() & df['lon'].notna()].copy()
    df_errors = df[df['lat'].isna() | df['lon'].isna()].copy()
    
    # Save to state-specific cache directory
    cache_dir = workspace_path / "cache" / state_abbr
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Save successfully geocoded addresses
    output_path = cache_dir / "geocoded.csv"
    df_success.to_csv(output_path, index=False)
    
    print(f"✓ Successfully geocoded {len(df_success)} addresses saved to: {output_path}")
    
    # Save failed geocodes to separate error file if any exist
    if len(df_errors) > 0:
        # Ensure street2 column exists for error file (required by API)
        if 'street2' not in df_errors.columns:
            df_errors['street2'] = ''
        
        error_path = cache_dir / "geocoded-errors.csv"
        df_errors.to_csv(error_path, index=False)
        
        error_msg = (
            f"⚠️  WARNING: {len(df_errors)} address(es) could not be geocoded!\n"
            f"   Failed addresses saved to: {error_path}\n"
            f"   These addresses will be excluded from route planning.\n"
            f"   Please review and correct the addresses, then re-run geocoding."
        )
        print(error_msg)
        
        # Raise an error to notify the caller
        raise ValueError(
            f"Geocoding completed with {len(df_errors)} error(s). "
            f"See {error_path} for details. "
            f"Successfully geocoded {len(df_success)} addresses."
        )
    
    return output_path


def cluster(workspace_name: str, state_abbr: str, max_diameter_miles: float = 100) -> Path:
    """
    Cluster geocoded sites based on their geographic coordinates with diameter constraints.
    
    Uses automatic k-means clustering with optimal cluster count determined
    by silhouette score and geographic constraints. Iteratively splits clusters
    that exceed the maximum diameter to ensure teams don't have to travel
    excessive distances within a cluster.
    
    Reads from cache/{state_abbr}/geocoded.csv and saves results to 
    cache/{state_abbr}/clustered.csv.
    
    Args:
        workspace_name: Name of the workspace containing geocoded.csv
        state_abbr: State abbreviation (e.g., "LA", "NC")
        max_diameter_miles: Maximum allowed cluster diameter in miles (default: 100).
                           Recommended values:
                           - Tight (50-75): Dense urban areas, shorter workdays
                           - Normal (100): Recommended for most scenarios
                           - Loose (125-150): Rural areas, longer workdays
        
    Returns:
        Path to the created clustered.csv file
        
    Raises:
        FileNotFoundError: If workspace or geocoded.csv doesn't exist
        ValueError: If geocoded.csv has invalid data
    """
    from .data_prep.cluster import cluster_sites
    from .core.workspace import validate_workspace, validate_state_file
    
    # Validate workspace and geocoded file
    workspace_path = validate_workspace(workspace_name)
    geocoded_csv = validate_state_file(workspace_path, state_abbr, "geocoded.csv", "geocoded.csv")
    
    # Read geocoded data
    df = pd.read_csv(geocoded_csv)
    print(f"Clustering {len(df)} sites for state '{state_abbr}' from {geocoded_csv}...")
    print(f"Using max cluster diameter: {max_diameter_miles} miles")
    
    # Perform clustering with diameter constraint
    df_clustered = cluster_sites(df, max_diameter_miles=max_diameter_miles)
    
    # Save to state-specific cache directory
    output_path = workspace_path / "cache" / state_abbr / "clustered.csv"
    df_clustered.to_csv(output_path, index=False)
    
    print(f"✓ Clustered sites for state '{state_abbr}' saved to: {output_path}")
    
    return output_path


def plan(request: PlanRequest) -> PlanResult:
    """
    Plan routes for teams/crews to visit sites.
    
    Automatically selects the appropriate planning strategy:
    - Cluster-based planning if use_clusters=True
    - Fixed calendar mode if start_date and end_date provided
    - Fixed crew mode otherwise
    
    Sites can be provided explicitly or auto-loaded from geocoded.csv filtered by state_abbr.
    
    Args:
        request: Planning request with sites, constraints, and mode parameters
        
    Returns:
        PlanResult with optimized routes
        
    Raises:
        ValueError: If request validation fails
        FileNotFoundError: If required workspace files don't exist
    """
    return execute_plan(request)
