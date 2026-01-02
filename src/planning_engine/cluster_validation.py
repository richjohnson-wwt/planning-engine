"""Cluster validation and recommendation utilities for UI integration."""

from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd
from .paths import get_workspace_path


def get_cluster_info(workspace_name: str, state_abbr: str) -> Optional[Dict[str, Any]]:
    """
    Get cluster information for a workspace and state.
    
    Returns cluster count and size distribution to help users make informed
    decisions about crew allocation.
    
    Args:
        workspace_name: Name of the workspace
        state_abbr: State abbreviation (e.g., "DC", "LA")
        
    Returns:
        Dict with cluster info, or None if clustered.csv doesn't exist:
        {
            "cluster_count": int,
            "total_sites": int,
            "cluster_sizes": {cluster_id: site_count},
            "recommended_min_crews": int,
            "clustered_file_exists": bool
        }
    """
    try:
        workspace_path = get_workspace_path(workspace_name)
        clustered_csv = workspace_path / "cache" / state_abbr / "clustered.csv"
        
        if not clustered_csv.exists():
            return {
                "clustered_file_exists": False,
                "cluster_count": 0,
                "total_sites": 0,
                "cluster_sizes": {},
                "recommended_min_crews": 0
            }
        
        # Read clustered data
        df = pd.read_csv(clustered_csv)
        
        # Get cluster information
        cluster_ids = sorted([int(cid) for cid in df['cluster_id'].unique()])
        cluster_sizes = {}
        for cluster_id in cluster_ids:
            cluster_df = df[df['cluster_id'] == cluster_id]
            cluster_sizes[cluster_id] = len(cluster_df)
        
        total_sites = len(df)
        cluster_count = len(cluster_ids)
        
        # Recommended minimum crews = number of clusters
        # This ensures each cluster gets at least 1 crew
        recommended_min_crews = cluster_count
        
        return {
            "clustered_file_exists": True,
            "cluster_count": cluster_count,
            "total_sites": total_sites,
            "cluster_sizes": cluster_sizes,
            "recommended_min_crews": recommended_min_crews
        }
        
    except Exception as e:
        print(f"Error getting cluster info: {e}")
        return None


def validate_cluster_crew_allocation(
    workspace_name: str,
    state_abbr: str,
    requested_crews: int
) -> Dict[str, Any]:
    """
    Validate if the requested crew count is sufficient for cluster-based planning.
    
    Provides warnings and recommendations for the UI to display to users.
    
    Args:
        workspace_name: Name of the workspace
        state_abbr: State abbreviation
        requested_crews: Number of crews the user wants to use
        
    Returns:
        Dict with validation results:
        {
            "is_valid": bool,
            "cluster_count": int,
            "requested_crews": int,
            "recommended_crews": int,
            "warning_message": str or None,
            "unassigned_sites_estimate": int,
            "clusters_skipped": int
        }
    """
    cluster_info = get_cluster_info(workspace_name, state_abbr)
    
    if not cluster_info or not cluster_info["clustered_file_exists"]:
        return {
            "is_valid": False,
            "cluster_count": 0,
            "requested_crews": requested_crews,
            "recommended_crews": 0,
            "warning_message": "Clustered data not found. Please run clustering first.",
            "unassigned_sites_estimate": 0,
            "clusters_skipped": 0
        }
    
    cluster_count = cluster_info["cluster_count"]
    total_sites = cluster_info["total_sites"]
    cluster_sizes = cluster_info["cluster_sizes"]
    
    # Check if crews are sufficient
    if requested_crews >= cluster_count:
        # Sufficient crews - all clusters can be planned
        return {
            "is_valid": True,
            "cluster_count": cluster_count,
            "requested_crews": requested_crews,
            "recommended_crews": cluster_count,
            "warning_message": None,
            "unassigned_sites_estimate": 0,
            "clusters_skipped": 0
        }
    else:
        # Insufficient crews - some clusters will be skipped
        clusters_skipped = cluster_count - requested_crews
        
        # Estimate unassigned sites (smallest clusters will be skipped)
        sorted_clusters = sorted(cluster_sizes.items(), key=lambda x: x[1])
        unassigned_sites = sum(size for _, size in sorted_clusters[:clusters_skipped])
        
        warning_message = (
            f"Warning: {requested_crews} crews is insufficient for {cluster_count} clusters. "
            f"Approximately {clusters_skipped} cluster(s) with ~{unassigned_sites} site(s) will be skipped. "
            f"Recommended: Increase crews to {cluster_count} or disable clustering."
        )
        
        return {
            "is_valid": False,
            "cluster_count": cluster_count,
            "requested_crews": requested_crews,
            "recommended_crews": cluster_count,
            "warning_message": warning_message,
            "unassigned_sites_estimate": unassigned_sites,
            "clusters_skipped": clusters_skipped
        }


def get_cluster_recommendation_message(workspace_name: str, state_abbr: str) -> str:
    """
    Get a user-friendly recommendation message for cluster-based planning.
    
    This can be displayed in the UI when the user enables clustering.
    
    Args:
        workspace_name: Name of the workspace
        state_abbr: State abbreviation
        
    Returns:
        Formatted recommendation message for the UI
    """
    cluster_info = get_cluster_info(workspace_name, state_abbr)
    
    if not cluster_info or not cluster_info["clustered_file_exists"]:
        return "⚠️ Clustered data not found. Please run clustering first before enabling cluster-based planning."
    
    cluster_count = cluster_info["cluster_count"]
    total_sites = cluster_info["total_sites"]
    
    message = (
        f"ℹ️ Cluster-based planning detected {cluster_count} geographic clusters "
        f"with {total_sites} total sites.\n\n"
        f"📊 Cluster distribution:\n"
    )
    
    for cluster_id, size in sorted(cluster_info["cluster_sizes"].items()):
        percentage = (size / total_sites) * 100
        message += f"  • Cluster {cluster_id}: {size} sites ({percentage:.1f}%)\n"
    
    message += (
        f"\n💡 Planning Strategy:\n"
        f"  • Fixed Crew Mode: Crews work sequentially through all clusters. "
        f"With fewer crews than clusters, planning takes longer but all sites are covered.\n"
        f"  • Calendar Mode: Each cluster planned independently within the date range.\n\n"
        f"🎯 Optimal: Use {cluster_count}+ crews for fastest parallel planning.\n"
        f"✓ Acceptable: Use fewer crews - all sites will still be planned over more days."
    )
    
    return message
