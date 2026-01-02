"""Virtual depot creation for OR-Tools routing.

Note: The 'depot' is a virtual centroid used for OR-Tools calculations only.
It is NOT a physical office location. Crews are hired locally in each city.
Routes start at the first site and end at the last site.
"""

from typing import List
from ..models import Site


def create_virtual_depot(sites: List[Site]) -> Site:
    """
    Create a virtual depot at the geographic centroid of sites.
    
    This depot is used by OR-Tools for routing calculations but does NOT
    represent a physical location. Routes start at the first site and end
    at the last site in the optimized route.
    
    Args:
        sites: List of sites to calculate centroid from
        
    Returns:
        Virtual depot Site at the centroid with service_minutes=0
    """
    if not sites:
        # Default to 0,0 if no sites (edge case)
        return Site(
            id="DEPOT",
            name="Virtual Depot (Centroid)",
            lat=0.0,
            lon=0.0,
            service_minutes=0,
            index=0
        )
    
    avg_lat = sum(s.lat for s in sites) / len(sites)
    avg_lon = sum(s.lon for s in sites) / len(sites)
    
    return Site(
        id="DEPOT",
        name="Virtual Depot (Centroid)",
        lat=avg_lat,
        lon=avg_lon,
        service_minutes=0,
        index=0
    )
