"""Sequential cluster planning: crews work through clusters one after another."""

from datetime import date, timedelta
from typing import List, Dict, Set
from ..models import PlanRequest, CalendarPlanResult, Site, TeamDay, TeamConfig
from ..core.depot import create_virtual_depot
from ..solver.solver_utils import prepare_sites_with_indices, calculate_distance_matrix
from ..solver.ortools_solver import solve_single_day_vrptw, _convert_solution_to_team_days
from .crew_planner import _is_non_working_day, _remove_assigned_sites


def plan_clusters_sequentially(
    request: PlanRequest,
    cluster_data: Dict[int, List[Site]]
) -> CalendarPlanResult:
    """
    Plan clusters sequentially with fixed crews working through all clusters over time.
    
    This approach allows crews to move to new clusters after completing their assigned
    cluster, ensuring all sites get planned even with fewer crews than clusters.
    
    Strategy:
    1. Start with all crews available
    2. Assign crews to clusters (prioritize larger clusters)
    3. Plan each cluster day-by-day until complete
    4. When a crew finishes their cluster, assign them to a remaining cluster
    5. Continue until all clusters are planned or max days reached
    
    Args:
        request: Planning request with fixed crew mode (no end_date)
        cluster_data: Dict mapping cluster_id to list of sites
        
    Returns:
        CalendarPlanResult with all clusters planned sequentially
    """
    total_crews = request.team_config.teams
    cluster_ids = sorted(cluster_data.keys())
    
    print(f"  Sequential planning: {total_crews} crews working through {len(cluster_ids)} clusters")
    
    # Track which clusters are complete and which crews are working on which cluster
    completed_clusters: Set[int] = set()
    cluster_assignments: Dict[int, int] = {}  # crew_id -> cluster_id
    cluster_sites_remaining: Dict[int, List[Site]] = {
        cid: list(sites) for cid, sites in cluster_data.items()
    }
    
    # Assign initial clusters to crews (prioritize larger clusters)
    sorted_clusters = sorted(
        cluster_data.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )
    
    for crew_id in range(1, total_crews + 1):
        if sorted_clusters:
            cluster_id, _ = sorted_clusters.pop(0)
            cluster_assignments[crew_id] = cluster_id
            print(f"    Crew {crew_id} → Cluster {cluster_id} ({len(cluster_data[cluster_id])} sites)")
    
    # Planning loop
    all_team_days: List[TeamDay] = []
    current_date = request.start_date or date.today()
    planning_days_used = 0
    consecutive_no_progress_days = 0
    
    MAX_PLANNING_DAYS = 365
    MAX_CONSECUTIVE_NO_PROGRESS = 5
    
    while len(completed_clusters) < len(cluster_ids) and planning_days_used < MAX_PLANNING_DAYS:
        # Skip non-working days
        if _is_non_working_day(current_date, request.holidays):
            current_date += timedelta(days=1)
            continue
        
        planning_days_used += 1
        day_had_progress = False
        
        # Plan for each crew working on their assigned cluster
        for crew_id in range(1, total_crews + 1):
            if crew_id not in cluster_assignments:
                continue  # Crew has no assignment (all clusters done)
            
            cluster_id = cluster_assignments[crew_id]
            sites_remaining = cluster_sites_remaining[cluster_id]
            
            if not sites_remaining:
                # This cluster is complete
                completed_clusters.add(cluster_id)
                print(f"    ✓ Cluster {cluster_id} complete (Crew {crew_id})")
                
                # Assign this crew to a new cluster if available
                unassigned_clusters = [
                    cid for cid in cluster_ids
                    if cid not in completed_clusters and cid not in cluster_assignments.values()
                ]
                
                if unassigned_clusters:
                    # Assign to largest remaining cluster
                    next_cluster = max(unassigned_clusters, key=lambda cid: len(cluster_sites_remaining[cid]))
                    cluster_assignments[crew_id] = next_cluster
                    print(f"    Crew {crew_id} → Cluster {next_cluster} ({len(cluster_sites_remaining[next_cluster])} sites)")
                else:
                    # No more clusters to assign
                    del cluster_assignments[crew_id]
                
                continue
            
            # Plan this crew's work for today on their assigned cluster
            depot = create_virtual_depot(sites_remaining)
            sites_with_depot = prepare_sites_with_indices(sites_remaining, depot)
            distance_matrix_minutes = calculate_distance_matrix(sites_with_depot)
            
            # Create a single-crew request for this crew
            single_crew_request = request.model_copy(update={
                "team_config": TeamConfig(teams=1, workday=request.team_config.workday)
            })
            
            solution = solve_single_day_vrptw(
                sites=sites_with_depot,
                request=single_crew_request,
                distance_matrix_minutes=distance_matrix_minutes,
            )
            
            if solution and solution.get("total_sites_scheduled", 0) > 0:
                # Convert solution and assign to this specific crew
                day_team_days = _convert_solution_to_team_days(
                    solution,
                    sites_with_depot,
                    request.break_minutes
                )
                
                # Update team IDs and dates
                for td in day_team_days:
                    td.team_id = crew_id
                    td.date = current_date
                    td._cluster_id = cluster_id  # Track for debugging
                
                all_team_days.extend(day_team_days)
                
                # Remove assigned sites from remaining
                _remove_assigned_sites(sites_remaining, day_team_days)
                cluster_sites_remaining[cluster_id] = sites_remaining
                
                day_had_progress = True
                consecutive_no_progress_days = 0
        
        if not day_had_progress:
            consecutive_no_progress_days += 1
            if consecutive_no_progress_days >= MAX_CONSECUTIVE_NO_PROGRESS:
                print(f"    ⚠️ No progress for {consecutive_no_progress_days} days, stopping")
                break
        
        current_date += timedelta(days=1)
    
    # Calculate unassigned sites
    total_unassigned = sum(len(sites) for sites in cluster_sites_remaining.values())
    
    # Determine date range
    if all_team_days:
        dates = [td.date for td in all_team_days if td.date]
        start_date = min(dates)
        end_date = max(dates)
    else:
        start_date = request.start_date or date.today()
        end_date = start_date
    
    print(f"  Sequential planning complete:")
    print(f"    • Clusters completed: {len(completed_clusters)}/{len(cluster_ids)}")
    print(f"    • Team-days: {len(all_team_days)}")
    print(f"    • Planning days used: {planning_days_used}")
    print(f"    • Unassigned sites: {total_unassigned}")
    
    return CalendarPlanResult(
        start_date=start_date,
        end_date=end_date,
        team_days=all_team_days,
        unassigned=total_unassigned,
        crews_used=total_crews,
        planning_days_used=planning_days_used
    )
