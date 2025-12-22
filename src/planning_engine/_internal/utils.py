from math import radians, sin, cos, sqrt, atan2
from typing import List
from ..models import Site


def calculate_distance_matrix(sites: List[Site], avg_speed_kmh: float = 60.0) -> List[List[int]]:
    """Calculate travel time matrix including service time at destination.
    
    Returns a matrix where matrix[i][j] represents the time to travel from i to j
    PLUS the service time at j. This ensures the solver accounts for service time.
    """
    def haversine_distance(lat1, lon1, lat2, lon2) -> float:
        R = 6371
        lat1_rad, lon1_rad = radians(lat1), radians(lon1)
        lat2_rad, lon2_rad = radians(lat2), radians(lon2)
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c

    n = len(sites)
    matrix = []
    for i in range(n):
        row = []
        for j in range(n):
            if i == j:
                row.append(0)
            else:
                dist_km = haversine_distance(sites[i].lat, sites[i].lon, sites[j].lat, sites[j].lon)
                travel_min = int((dist_km / avg_speed_kmh) * 60)
                # Add service time at destination (j) to account for total time
                total_time = travel_min + sites[j].service_minutes
                row.append(total_time)
        matrix.append(row)
    return matrix