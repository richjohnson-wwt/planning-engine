# ortools_solver.py (patched)

from datetime import date, datetime, timedelta
from typing import List, Optional
from math import radians, sin, cos, sqrt, atan2

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

from .models import Site, PlanRequest, PlanResult, TeamDay
from ._internal.utils import calculate_distance_matrix

DEPOT_INDEX = 0  # synthetic depot index

def plan_single_day_vrp(request: PlanRequest) -> PlanResult:
    """Plan single-day vehicle routes using OR-Tools VRP solver.
    
    Optimizes routes for one day given a set of sites and crew constraints.
    Does NOT schedule across multiple days - each call optimizes one day.
    
    Args:
        request: Planning request with sites, crew config, and constraints
        
    Returns:
        PlanResult with optimized routes for one day
    """
    # Create synthetic depot at centroid of real sites
    if request.sites:
        avg_lat = sum(s.lat for s in request.sites) / len(request.sites)
        avg_lon = sum(s.lon for s in request.sites) / len(request.sites)
    else:
        avg_lat, avg_lon = 0.0, 0.0
    
    depot_site = Site(
        id="DEPOT",
        name="DEPOT",
        lat=avg_lat,
        lon=avg_lon,
        service_minutes=0,
        index=0
    )

    # Prepend depot to sites list
    sites = [depot_site] + request.sites

    # Assign indices to all sites
    for idx, site in enumerate(sites):
        site.index = idx
        assert site.index is not None

    distance_matrix_minutes = calculate_distance_matrix(sites)

    solution = solve_single_day_vrptw(sites, request, distance_matrix_minutes)

    if not solution:
        return PlanResult(team_days=[], unassigned=len(request.sites))

    team_days = _convert_solution_to_team_days(solution, sites)

    return PlanResult(team_days=team_days, unassigned=solution.get("unassigned", 0))



# def _calculate_distance_matrix(sites: List[Site], avg_speed_kmh: float = 60.0) -> List[List[int]]:
#     """Calculate travel time matrix including service time at destination.
    
#     Returns a matrix where matrix[i][j] represents the time to travel from i to j
#     PLUS the service time at j. This ensures the solver accounts for service time.
#     """
#     def haversine_distance(lat1, lon1, lat2, lon2) -> float:
#         R = 6371
#         lat1_rad, lon1_rad = radians(lat1), radians(lon1)
#         lat2_rad, lon2_rad = radians(lat2), radians(lon2)
#         dlat = lat2_rad - lat1_rad
#         dlon = lon2_rad - lon1_rad
#         a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon/2)**2
#         c = 2 * atan2(sqrt(a), sqrt(1-a))
#         return R * c

#     n = len(sites)
#     matrix = []
#     for i in range(n):
#         row = []
#         for j in range(n):
#             if i == j:
#                 row.append(0)
#             else:
#                 dist_km = haversine_distance(sites[i].lat, sites[i].lon, sites[j].lat, sites[j].lon)
#                 travel_min = int((dist_km / avg_speed_kmh) * 60)
#                 # Add service time at destination (j) to account for total time
#                 total_time = travel_min + sites[j].service_minutes
#                 row.append(total_time)
#         matrix.append(row)
#     return matrix


def _convert_solution_to_team_days(solution: dict, sites: List[Site]) -> List[TeamDay]:
    team_days = []

    for route in solution.get("routes", []):
        crew_id = route["crew_id"]
        visits = route["visits"]

        site_ids = []
        route_sites = []  # Collect full Site objects
        total_service = 0
        total_route = 0

        for visit in visits:
            if visit["site"] == "DEPOT":
                continue  # skip synthetic depot
            site = next((s for s in sites if s.name == visit["site"]), None)
            if site:
                site_ids.append(site.id)
                route_sites.append(site)  # Add full Site object
                total_service += site.service_minutes
                total_route += site.service_minutes + visit.get("travel_minutes", 0)

        if site_ids:
            td = TeamDay(
                team_id=crew_id + 1,
                site_ids=site_ids,
                sites=route_sites,  # Include full Site objects for mapping
                total_minutes=total_service,
                service_minutes=total_service,
                route_minutes=total_route
            )
            team_days.append(td)

    return team_days


def _create_data_model(sites: List[Site], travel_time_matrix: List[List[int]]) -> dict:
    return {
        "distance_matrix": travel_time_matrix,
        "num_locations": len(sites),
        "depot": DEPOT_INDEX
    }


def solve_single_day_vrptw(sites: List[Site], request: PlanRequest, distance_matrix_minutes: List[List[int]]) -> Optional[dict]:
    """Solve single-day Vehicle Routing Problem with Time Windows using OR-Tools.
    
    This is a single-day optimizer - it does not schedule across multiple days.
    
    Args:
        sites: List of sites including synthetic depot at index 0
        request: Planning request with constraints
        distance_matrix_minutes: Travel time matrix including service times
        
    Returns:
        Solution dict with routes, or None if no solution found
    """
    if len(sites) < 2:
        return {
            "routes": [{
                "crew_id": 0,
                "visits": [{
                    "site": sites[0].name if sites else "",
                    "arrival": request.start_date,
                    "service_minutes": sites[0].service_minutes if sites else 0
                }] if sites else []
            }],
            "used_crews": 1 if sites else 0,
            "total_sites_scheduled": len(sites),
            "unassigned": 0
        }

    data = _create_data_model(sites, distance_matrix_minutes)

    service_time = request.service_minutes_per_site
    time_per_site = service_time + 15  # assume 15 min avg travel
    max_sites_per_vehicle = max(1, int(request.max_route_minutes / time_per_site))
    estimated_vehicles = max(1, (len(sites) + max_sites_per_vehicle - 1) // max_sites_per_vehicle)

    # Use team_config.teams for number of vehicles (fixed-crews mode)
    num_vehicles = min(estimated_vehicles, request.get_num_crews())

    manager = pywrapcp.RoutingIndexManager(data["num_locations"], num_vehicles, data["depot"])
    routing = pywrapcp.RoutingModel(manager)

    # Distance callback
    def distance_callback(from_index, to_index):
        return data["distance_matrix"][manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Add time dimension
    # Parameters: callback, slack_max, capacity, fix_start_cumul_to_zero, name
    # fix_start_cumul_to_zero=False allows vehicles to start at different times
    # In fast_mode, allow more slack for faster feasibility checks
    slack_max = 30 if request.fast_mode else 0
    time_dimension_name = "Time"
    routing.AddDimension(transit_callback_index,
                         slack_max,  # slack_max: waiting time allowed at each location
                         request.max_route_minutes,  # capacity: max route duration
                         False,  # fix_start_cumul_to_zero: False for flexibility
                         time_dimension_name)
    time_dimension = routing.GetDimensionOrDie(time_dimension_name)

    # Set time window for depot: must start at time 0
    depot_index = manager.NodeToIndex(DEPOT_INDEX)
    time_dimension.CumulVar(depot_index).SetRange(0, 0)
    
    # Other sites don't need explicit time windows - the dimension capacity
    # (max_route_minutes) already constrains the total route duration

    # --- PATCHED: disjunctions to allow skipping sites ---
    PENALTY = 10_000
    for site in sites:
        if site.index == DEPOT_INDEX:
            continue
        index = manager.NodeToIndex(site.index)
        routing.AddDisjunction([index], PENALTY)

    # Search parameters
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
     
    # Adjust time limit based on fast_mode
    if request.fast_mode:
        search_parameters.time_limit.seconds = 1
        search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.AUTOMATIC
        search_parameters.lns_time_limit.seconds = 0
    else:
        search_parameters.time_limit.seconds = 15
        search_parameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
        search_parameters.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    
    search_parameters.log_search = False

    solution = routing.SolveWithParameters(search_parameters)
    if not solution:
        return {
            "routes": [],
            "used_crews": 0,
            "total_sites_scheduled": 0,
            "unassigned": len(sites) - 1
        }

    # Extract solution
    return _extract_solution(routing, manager, solution, sites, request.start_date, time_dimension)


def _extract_solution(routing, manager, solution, sites, start_date, time_dimension):
    """Extract solution from OR-Tools routing model.
    
    Note: The distance matrix includes service time at destination, so we need to
    subtract service time to get pure travel time for reporting purposes.
    """
    routes = []
    total_sites = 0
    used_vehicles = 0

    for vehicle_id in range(routing.vehicles()):
        index = routing.Start(vehicle_id)
        route = []
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            site = sites[node_index]
            time_var = time_dimension.CumulVar(index)
            arrival = solution.Value(time_var)
            arrival_date = start_date + timedelta(minutes=arrival) if start_date else arrival
            
            # Get arc cost to next node (includes travel + service at next node)
            next_index = solution.Value(routing.NextVar(index))
            if not routing.IsEnd(next_index):
                arc_cost = routing.GetArcCostForVehicle(index, next_index, vehicle_id)
                next_node = manager.IndexToNode(next_index)
                next_site = sites[next_node]
                # Subtract service time at next site to get pure travel time
                travel_min = arc_cost - next_site.service_minutes
            else:
                travel_min = 0

            route.append({
                "site": site.name,
                "arrival": arrival_date,
                "service_minutes": site.service_minutes,
                "travel_minutes": travel_min
            })
            total_sites += 1
            index = next_index

        if route:
            used_vehicles += 1
            routes.append({"crew_id": vehicle_id, "visits": route})

    # Calculate unassigned sites (excluding depot from count)
    # total_sites includes depot visits, so we need to subtract depot from both counts
    unassigned = (len(sites) - 1) - (total_sites - used_vehicles)
    return {
        "routes": routes,
        "used_crews": used_vehicles,
        "total_sites_scheduled": total_sites - used_vehicles,  # Exclude depot visits
        "unassigned": unassigned
    }
