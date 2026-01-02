"""Utilities for solver operations: distance matrix, site preparation."""

from typing import List
from ..models import Site
from .._internal.utils import calculate_distance_matrix as _calc_distance_matrix


def calculate_distance_matrix(sites: List[Site], avg_speed_kmh: float = 60.0) -> List[List[int]]:
    """
    Calculate distance matrix between all sites in minutes.
    
    Args:
        sites: List of sites including depot (if applicable)
        avg_speed_kmh: Average travel speed in km/h
        
    Returns:
        Distance matrix in minutes (2D list)
    """
    return _calc_distance_matrix(sites, avg_speed_kmh)


def prepare_sites_with_indices(sites: List[Site], depot: Site) -> List[Site]:
    """
    Prepare sites list with depot at index 0 and assign indices to all sites.
    
    Args:
        sites: List of sites to prepare
        depot: Virtual depot site (centroid)
        
    Returns:
        List with depot at index 0, followed by sites, all with indices assigned
    """
    sites_with_depot = [depot] + sites
    for idx, site in enumerate(sites_with_depot):
        site.index = idx
    return sites_with_depot
