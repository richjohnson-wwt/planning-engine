"""OR-Tools VRP solver for route optimization."""

from datetime import date, datetime, timedelta
from typing import List, Optional
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

from ..models import Site, PlanRequest, TeamDay

DEPOT_INDEX = 0  # Virtual depot index (centroid, not physical location)


def _convert_solution_to_team_days(
    solution: dict,
    sites: List[Site],
    break_minutes: int = 0
) -> List[TeamDay]:
    """
    Convert OR-Tools solution to TeamDay objects.
    
    Args:
        solution: Solution dict from OR-Tools solver
        sites: List of sites including depot at index 0
        break_minutes: Break time in minutes to add to each route
        
    Returns:
        List of TeamDay objects
    """
    team_days = []

    for route in solution.get("routes", []):
        crew_id = route["crew_id"]
        visits = route["visits"]

        site_ids = []
        route_sites = []
        total_service = 0
        total_travel = 0
        total_route = 0

        for visit in visits:
            if visit["site"] == "Virtual Depot (Centroid)":
                continue  # Skip virtual depot
            site = next((s for s in sites if s.name == visit["site"]), None)
            if site:
                site_ids.append(site.id)
                route_sites.append(site)
                total_service += site.service_minutes
                travel_min = visit.get("travel_minutes", 0)
                total_travel += travel_min
                total_route += site.service_minutes + travel_min

        if site_ids:
            td = TeamDay(
                team_id=crew_id + 1,
                site_ids=site_ids,
                sites=route_sites,
                total_minutes=total_service,
                service_minutes=total_service,
                travel_minutes=total_travel,
                route_minutes=total_route,
                break_minutes=break_minutes
            )
            team_days.append(td)

    return team_days


def _create_data_model(sites: List[Site], travel_time_matrix: List[List[int]]) -> dict:
    """Create data model for OR-Tools solver."""
    return {
        "distance_matrix": travel_time_matrix,
        "num_locations": len(sites),
        "depot": DEPOT_INDEX
    }


def solve_single_day_vrptw(
    sites: List[Site],
    request: PlanRequest,
    distance_matrix_minutes: List[List[int]]
) -> Optional[dict]:
    """
    Solve single-day Vehicle Routing Problem with Time Windows using OR-Tools.
    
    This is a single-day optimizer - it does not schedule across multiple days.
    
    Args:
        sites: List of sites including virtual depot at index 0
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
    time_per_site = service_time + 15  # Assume 15 min avg travel
    max_sites_per_vehicle = max(1, int(request.max_route_minutes / time_per_site))
    estimated_vehicles = max(1, (len(sites) + max_sites_per_vehicle - 1) // max_sites_per_vehicle)

    # Use team_config.teams for number of vehicles
    num_vehicles = min(estimated_vehicles, request.get_num_crews())

    manager = pywrapcp.RoutingIndexManager(data["num_locations"], num_vehicles, data["depot"])
    routing = pywrapcp.RoutingModel(manager)

    # Distance callback
    def distance_callback(from_index, to_index):
        return data["distance_matrix"][manager.IndexToNode(from_index)][manager.IndexToNode(to_index)]

    transit_callback_index = routing.RegisterTransitCallback(distance_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Add time dimension
    slack_max = 30 if request.fast_mode else 0
    time_dimension_name = "Time"
    
    # Calculate effective route time: max_route_minutes minus break_minutes
    effective_route_minutes = request.max_route_minutes - request.break_minutes
    
    routing.AddDimension(
        transit_callback_index,
        slack_max,  # Waiting time allowed at each location
        effective_route_minutes,  # Max route duration (minus break time)
        False,  # Don't fix start cumul to zero for flexibility
        time_dimension_name
    )
    time_dimension = routing.GetDimensionOrDie(time_dimension_name)

    # Set time window for depot: must start at time 0
    depot_index = manager.NodeToIndex(DEPOT_INDEX)
    time_dimension.CumulVar(depot_index).SetRange(0, 0)

    # Add disjunctions to allow skipping sites if needed
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
    """
    Extract solution from OR-Tools routing model.
    
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
    unassigned = (len(sites) - 1) - (total_sites - used_vehicles)
    return {
        "routes": routes,
        "used_crews": used_vehicles,
        "total_sites_scheduled": total_sites - used_vehicles,  # Exclude depot visits
        "unassigned": unassigned
    }


def solve_vrptw(request: PlanRequest) -> dict:
    """
    Solve VRPTW for a single day using the provided request.
    
    This is a convenience wrapper that prepares sites with depot and calls
    the solver. For multi-day planning, call this function once per day.
    
    Args:
        request: Planning request with sites and constraints
        
    Returns:
        Solution dict with routes
    """
    from ..core.depot import create_virtual_depot
    from .solver_utils import prepare_sites_with_indices, calculate_distance_matrix
    
    if not request.sites:
        return {
            "routes": [],
            "used_crews": 0,
            "total_sites_scheduled": 0,
            "unassigned": 0
        }
    
    # Create virtual depot and prepare sites
    depot = create_virtual_depot(request.sites)
    sites_with_depot = prepare_sites_with_indices(request.sites, depot)
    
    # Calculate distance matrix
    distance_matrix = calculate_distance_matrix(sites_with_depot)
    
    # Solve
    return solve_single_day_vrptw(sites_with_depot, request, distance_matrix)


def plan_single_day_vrp(request: PlanRequest):
    """
    Legacy wrapper for backward compatibility with test scripts.
    
    Plan single-day vehicle routes using OR-Tools VRP solver.
    
    Args:
        request: Planning request with sites, crew config, and constraints
        
    Returns:
        PlanResult with optimized routes for one day
    """
    from ..models import PlanResult
    from ..core.depot import create_virtual_depot
    from .solver_utils import prepare_sites_with_indices, calculate_distance_matrix
    
    if not request.sites:
        return PlanResult(team_days=[], unassigned=0)
    
    # Create virtual depot and prepare sites
    depot = create_virtual_depot(request.sites)
    sites_with_depot = prepare_sites_with_indices(request.sites, depot)
    
    # Calculate distance matrix
    distance_matrix = calculate_distance_matrix(sites_with_depot)
    
    # Solve
    solution = solve_single_day_vrptw(sites_with_depot, request, distance_matrix)
    
    if not solution:
        return PlanResult(team_days=[], unassigned=len(request.sites))
    
    team_days = _convert_solution_to_team_days(solution, sites_with_depot, request.break_minutes)
    
    return PlanResult(team_days=team_days, unassigned=solution.get("unassigned", 0))
