# ortools_solver.py

from datetime import date, datetime, timedelta
from typing import List, Optional

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

from .models import Site, PlanRequest


def create_data_model(
    sites: List[Site],
    request: PlanRequest,
    travel_time_matrix: List[List[int]],  # minutes between all site nodes
) -> dict:
    """Creates the data dictionary for OR-Tools."""
    data = {}
    data["num_vehicles"] = request.num_crews_available
    # No depot - routes start at first site and end at last site
    data["starts"] = [0] * request.num_crews_available  # All start from node 0 (dummy start)
    data["ends"] = [0] * request.num_crews_available    # All end at node 0 (dummy end)

    # Time windows for each site: open during working days, exclude holidays/blackouts
    num_days = (request.end_date - request.start_date).days + 1
    minutes_per_day = 24 * 60

    time_windows = []
    for site in sites:
        earliest = 0
        latest = num_days * minutes_per_day

        # If site has blackouts, narrow window (advanced: could exclude intervals)
        # For simplicity here: assume site available any non-holiday day
        time_windows.append((earliest, latest))

    # Depot: open every working day during shift hours
    depot_windows = []
    current = request.start_date
    while current <= request.end_date:
        if current in request.holidays:
            current += timedelta(days=1)
            continue
        day_start_minutes = (current - request.start_date).days * minutes_per_day
        day_start = day_start_minutes + 8 * 60  # assume start at 8 AM
        day_end = day_start + request.daily_work_minutes
        depot_windows.append((day_start, day_end))
        current += timedelta(days=1)

    # OR-Tools requires one time window per node; we'll use the union (earliest to latest)
    # For strict daily returns, we rely on vehicle time limits and break scheduling
    data["time_windows"] = time_windows  # All sites have time windows

    data["service_times"] = [site.service_minutes for site in sites]
    data["travel_time_matrix"] = travel_time_matrix

    # Capacity: max sites per crew per day
    demands = [1 for _ in sites]  # Each site demands 1 "visit"
    vehicle_capacities = [request.max_sites_per_crew_per_day] * request.num_crews_available
    data["demands"] = demands
    data["vehicle_capacities"] = vehicle_capacities

    return data


def solve_vrptw(
    sites: List[Site],
    request: PlanRequest,
    distance_matrix_minutes: List[List[int]],
) -> Optional[dict]:
    """Solves multi-day VRPTW and returns solution."""
    data = create_data_model(sites, request, distance_matrix_minutes)

    # Create routing manager with start/end indices (no single depot)
    manager = pywrapcp.RoutingIndexManager(
        len(data["travel_time_matrix"]),
        data["num_vehicles"],
        data["starts"],
        data["ends"]
    )
    routing = pywrapcp.RoutingModel(manager)

    # Travel time callback
    def time_callback(from_index, to_index):
        from_node = manager.IndexToNode(from_index)
        to_node = manager.IndexToNode(to_index)
        return data["travel_time_matrix"][from_node][to_node] + data["service_times"][from_node]

    transit_callback_index = routing.RegisterTransitCallback(time_callback)
    routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

    # Add Time Window constraints
    time_dimension_name = "Time"
    routing.AddDimension(
        transit_callback_index,
        slack_max=60,  # allow some waiting
        capacity=(request.end_date - request.start_date).days * 24 * 60 * 2,  # big horizon
        fix_start_cumul_to_zero=True,
        name=time_dimension_name,
    )
    time_dimension = routing.GetDimensionOrDie(time_dimension_name)

    # Apply time windows to each site
    for location_idx, time_window in enumerate(data["time_windows"]):
        index = manager.NodeToIndex(location_idx)
        time_dimension.CumulVar(index).SetRange(time_window[0], time_window[1])

    # Capacity dimension (sites per day)
    def demand_callback(from_index):
        from_node = manager.IndexToNode(from_index)
        return data["demands"][from_node]

    demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
    routing.AddDimensionWithVehicleCapacity(
        demand_callback_index,
        slack_max=0,
        vehicle_capacities=data["vehicle_capacities"],
        fix_start_cumul_to_zero=True,
        name="Capacity",
    )

    # Set span upper bound for each vehicle (daily work time + break)
    if request.break_minutes > 0:
        max_time = request.daily_work_minutes + request.break_minutes
        for vehicle_id in range(data["num_vehicles"]):
            time_dimension.SetSpanUpperBoundForVehicle(max_time, vehicle_id)

    # Minimize number of crews used if requested
    if request.minimize_crews:
        # High fixed cost for each vehicle encourages using fewer crews
        routing.SetFixedCostOfAllVehicles(100000)

    # Search parameters
    search_parameters = pywrapcp.DefaultRoutingSearchParameters()
    search_parameters.first_solution_strategy = (
        routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
    )
    search_parameters.local_search_metaheuristic = (
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    )
    search_parameters.time_limit.seconds = 120  # adjust based on size

    solution = routing.SolveWithParameters(search_parameters)
    if not solution:
        return None

    # Extract routes...
    return extract_solution(routing, manager, solution, sites, request.start_date)


def extract_solution(routing, manager, solution, sites, start_date):
    """Extract human-readable routes with dates and times."""
    routes = []
    total_sites = 0
    used_vehicles = 0
    
    # Get the time dimension
    time_dimension = routing.GetDimensionOrDie("Time")

    for vehicle_id in range(routing.vehicles()):
        index = routing.Start(vehicle_id)
        route = []
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            # All nodes are sites (no depot)
            site = sites[node_index]
            time_var = time_dimension.CumulVar(index)
            arrival = solution.Value(time_var)
            arrival_date = start_date + timedelta(minutes=arrival)
            route.append({
                "site": site.name,
                "arrival": arrival_date,
                "service_minutes": site.service_minutes,
            })
            total_sites += 1
            index = solution.Value(routing.NextVar(index))

        if len(route) > 0:
            used_vehicles += 1
            routes.append({"crew_id": vehicle_id, "visits": route})

    return {
        "routes": routes,
        "used_crews": used_vehicles,
        "total_sites_scheduled": total_sites,
        "unassigned": len(sites) - total_sites,
    }