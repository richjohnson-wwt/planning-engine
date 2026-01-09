"""Cluster-based planning: plan each geographic cluster separately."""

from typing import List, Dict
from ..models import PlanRequest, PlanResult, Site
from ..core.site_loader import load_sites_from_clustered, create_sites_from_dataframe
from .calendar_planner import plan_fixed_calendar
from .crew_planner import plan_fixed_crews
from .sequential_cluster_planner import plan_clusters_sequentially


def plan_with_clusters(request: PlanRequest) -> PlanResult:
    """
    Plan routes using cluster-based approach.
    
    Loads sites from clustered.csv, groups by cluster_id, plans each cluster
    separately, and combines the results. This prevents geographic constraint
    issues by keeping routes within cluster boundaries.
    
    Args:
        request: Planning request with use_clusters=True
        
    Returns:
        Combined PlanResult from all clusters
        
    Raises:
        ValueError: If state_abbr not provided
        FileNotFoundError: If clustered.csv doesn't exist
    """
    # Load clustered data
    df = load_sites_from_clustered(
        request.workspace,
        request.state_abbr,
        request.service_minutes_per_site
    )
    
    # Get unique cluster IDs
    cluster_ids = sorted([int(cid) for cid in df['cluster_id'].unique()])
    num_clusters = len(cluster_ids)
    print(f"Planning {num_clusters} clusters for state '{request.state_abbr}'...")
    
    # Determine planning strategy based on mode
    is_calendar_mode = request.start_date is not None and request.end_date is not None
    
    if is_calendar_mode:
        # Calendar mode: Plan each cluster independently with all crews
        print(f"  Calendar mode: Each cluster can use up to {request.team_config.teams} crews")
        return _plan_clusters_independently_calendar(request, df, cluster_ids)
    else:
        # Fixed crew mode: Use sequential planning where crews work through clusters
        print(f"  Fixed crew mode: {request.team_config.teams} crews working sequentially through clusters")
        
        # Prepare cluster data
        cluster_data: Dict[int, List[Site]] = {}
        for cluster_id in cluster_ids:
            cluster_df = df[df['cluster_id'] == cluster_id]
            cluster_sites = create_sites_from_dataframe(cluster_df, request.service_minutes_per_site)
            cluster_data[cluster_id] = cluster_sites
            print(f"    Cluster {cluster_id}: {len(cluster_sites)} sites")
        
        # Use sequential planning
        calendar_result = plan_clusters_sequentially(request, cluster_data)
        
        # Apply team ID renumbering and generate cluster-based team labels (C#-T#)
        _renumber_team_ids(calendar_result.team_days, is_calendar_mode=False)
        
        return calendar_result.to_plan_result()


def _plan_clusters_independently_calendar(
    request: PlanRequest,
    df,
    cluster_ids: List[int]
) -> PlanResult:
    """
    Plan clusters independently for calendar mode.
    
    Each cluster is planned separately with the full crew count available,
    since calendar mode plans for a fixed date range.
    """
    all_team_days = []
    overall_start_date = None
    overall_end_date = None
    
    # Plan each cluster separately (calendar mode only)
    for cluster_id in cluster_ids:
        # Filter sites for this cluster
        cluster_df = df[df['cluster_id'] == cluster_id]
        cluster_sites = create_sites_from_dataframe(cluster_df, request.service_minutes_per_site)
        
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
            max_route_minutes=request.max_route_minutes,
            break_minutes=request.break_minutes,
            holidays=request.holidays,
            service_minutes_per_site=request.service_minutes_per_site,
            fast_mode=request.fast_mode
        )
        
        # Plan this cluster with fixed calendar mode
        print(f"  Planning cluster {cluster_id} with fixed calendar mode...")
        cluster_calendar_result = plan_fixed_calendar(cluster_request)
        cluster_result = cluster_calendar_result.to_plan_result()
        
        # Track the overall date range across all clusters
        if cluster_result.start_date:
            if overall_start_date is None or cluster_result.start_date < overall_start_date:
                overall_start_date = cluster_result.start_date
        if cluster_result.end_date:
            if overall_end_date is None or cluster_result.end_date > overall_end_date:
                overall_end_date = cluster_result.end_date
        
        # Tag each team-day with its cluster_id for proper renumbering
        for td in cluster_result.team_days:
            td._cluster_id = cluster_id
        all_team_days.extend(cluster_result.team_days)
        print(f"    ✓ Cluster {cluster_id}: {len(cluster_result.team_days)} team-days scheduled")
    
    # Renumber team IDs to avoid duplicates across clusters
    _renumber_team_ids(all_team_days, request.start_date is not None and request.end_date is not None)
    
    return PlanResult(
        team_days=all_team_days,
        unassigned=0,  # Clusters handle their own unassigned sites
        start_date=overall_start_date,
        end_date=overall_end_date
    )


def _renumber_team_ids(team_days: List, is_calendar_mode: bool) -> None:
    """
    Renumber team IDs to avoid duplicates across clusters.
    
    - Calendar Mode with Clustering: Renumber per cluster (clusters work in parallel)
    - Calendar Mode without Clustering: Each team-day gets unique ID
    - Crew Mode: Teams maintain their IDs across dates (same team works multiple days)
    """
    if is_calendar_mode:
        # Check if we have cluster information
        has_clusters = any(hasattr(td, '_cluster_id') for td in team_days)
        
        if has_clusters:
            # Calendar mode with clustering: Renumber per cluster
            # Clusters work in parallel in different geographic areas
            # Within each cluster, the same team can work multiple days
            from collections import defaultdict
            
            cluster_teams = defaultdict(list)
            for td in team_days:
                cluster_id = td._cluster_id if hasattr(td, '_cluster_id') else 0
                cluster_teams[cluster_id].append(td)
            
            # Renumber each cluster independently starting from 1
            for cluster_id, cluster_team_days in cluster_teams.items():
                # Sort by date and original team_id for consistent ordering
                cluster_team_days.sort(key=lambda td: (td.date or "", td.team_id))
                
                # Map original team IDs to new team IDs within this cluster
                team_id_map = {}
                next_team_id = 1
                
                for td in cluster_team_days:
                    original_team_id = td.team_id
                    if original_team_id not in team_id_map:
                        team_id_map[original_team_id] = next_team_id
                        next_team_id += 1
                    td.team_id = team_id_map[original_team_id]
        else:
            # Calendar mode without clustering: Each team-day is independent
            for idx, td in enumerate(team_days, start=1):
                td.team_id = idx
    else:
        # Crew mode: Group by cluster and date, then renumber
        # This ensures the same "team" within a cluster keeps the same ID across days
        from collections import defaultdict
        
        # Group by cluster and original team_id to track teams across days
        cluster_team_map = defaultdict(dict)
        next_global_team_id = 1
        
        # Sort by date to ensure consistent ordering
        team_days.sort(key=lambda td: (td.date or "", td._cluster_id if hasattr(td, '_cluster_id') else 0, td.team_id))
        
        for td in team_days:
            cluster_id = td._cluster_id if hasattr(td, '_cluster_id') else 0
            original_team_id = td.team_id
            
            # Create a unique key for this team within its cluster
            key = (cluster_id, original_team_id)
            
            if key not in cluster_team_map:
                cluster_team_map[key] = next_global_team_id
                next_global_team_id += 1
            
            td.team_id = cluster_team_map[key]
    
    # Convert temporary _cluster_id to permanent cluster_id for UI display
    # Also generate team_label with 1-based cluster numbering for better UX
    for td in team_days:
        if hasattr(td, '_cluster_id'):
            td.cluster_id = td._cluster_id
            # Generate team label with 1-based cluster numbering (C1, C2, C3...)
            # cluster_id is 0-based internally, so add 1 for display
            td.team_label = f"C{td._cluster_id + 1}-T{td.team_id}"
            delattr(td, '_cluster_id')
        else:
            # No clustering, just use team ID
            td.team_label = f"T{td.team_id}"
