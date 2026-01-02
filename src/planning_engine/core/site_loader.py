"""Site loading utilities from various CSV sources."""

from typing import List
import pandas as pd
from ..models import Site
from .workspace import validate_workspace, validate_state_file


def _build_address_from_row(row: pd.Series) -> str:
    """Build full address string from CSV row."""
    address_parts = []
    if 'street1' in row and pd.notna(row['street1']):
        address_parts.append(str(row['street1']))
    if 'city' in row and pd.notna(row['city']):
        address_parts.append(str(row['city']))
    if 'state' in row and pd.notna(row['state']):
        address_parts.append(str(row['state']))
    if 'zip' in row and pd.notna(row['zip']):
        address_parts.append(str(row['zip']))
    return ', '.join(address_parts) if address_parts else None


def _create_site_from_row(row: pd.Series, service_minutes: int) -> Site:
    """Create a Site object from a CSV row."""
    full_address = _build_address_from_row(row)
    
    return Site(
        id=str(row['site_id']),
        name=f"{row['city']} - {row['street1']}",
        lat=float(row['lat']),
        lon=float(row['lon']),
        address=full_address,
        service_minutes=service_minutes
    )


def load_sites_from_geocoded(
    workspace_name: str,
    state_abbr: str,
    service_minutes_per_site: int = 60
) -> List[Site]:
    """
    Load sites from workspace's state-specific geocoded.csv file.
    
    Args:
        workspace_name: Name of the workspace
        state_abbr: State abbreviation (e.g., "LA", "NC")
        service_minutes_per_site: Service time in minutes per site
        
    Returns:
        List of Site objects
        
    Raises:
        FileNotFoundError: If workspace or geocoded.csv doesn't exist
        ValueError: If state_abbr is not provided
    """
    if not state_abbr:
        raise ValueError(
            "state_abbr is required to load sites. "
            "Specify which state's sites to load (e.g., 'LA', 'NC')"
        )
    
    workspace_path = validate_workspace(workspace_name)
    geocoded_csv = validate_state_file(
        workspace_path,
        state_abbr,
        "geocoded.csv",
        "geocoded.csv"
    )
    
    df = pd.read_csv(geocoded_csv)
    sites = [_create_site_from_row(row, service_minutes_per_site) for _, row in df.iterrows()]
    
    return sites


def load_sites_from_clustered(
    workspace_name: str,
    state_abbr: str,
    service_minutes_per_site: int = 60
) -> pd.DataFrame:
    """
    Load clustered sites from workspace's state-specific clustered.csv file.
    
    Returns the full DataFrame with cluster_id column for grouping.
    
    Args:
        workspace_name: Name of the workspace
        state_abbr: State abbreviation (e.g., "LA", "NC")
        service_minutes_per_site: Service time in minutes per site
        
    Returns:
        DataFrame with cluster_id and site data
        
    Raises:
        FileNotFoundError: If workspace or clustered.csv doesn't exist
        ValueError: If state_abbr is not provided
    """
    if not state_abbr:
        raise ValueError(
            "state_abbr is required when loading clustered sites. "
            "Specify which state's clusters to load (e.g., 'LA', 'NC')"
        )
    
    workspace_path = validate_workspace(workspace_name)
    clustered_csv = validate_state_file(
        workspace_path,
        state_abbr,
        "clustered.csv",
        "clustered.csv"
    )
    
    df = pd.read_csv(clustered_csv)
    return df


def create_sites_from_dataframe(
    df: pd.DataFrame,
    service_minutes_per_site: int = 60
) -> List[Site]:
    """
    Convert a DataFrame of site data to Site objects.
    
    Args:
        df: DataFrame with site data (must have required columns)
        service_minutes_per_site: Service time in minutes per site
        
    Returns:
        List of Site objects
    """
    return [_create_site_from_row(row, service_minutes_per_site) for _, row in df.iterrows()]
