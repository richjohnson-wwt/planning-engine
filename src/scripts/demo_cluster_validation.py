"""Demo script showing how to use cluster validation for UI integration."""

from planning_engine import (
    get_cluster_info,
    validate_cluster_crew_allocation,
    get_cluster_recommendation_message
)


def demo_cluster_validation():
    """
    Demonstrate cluster validation utilities for UI integration.
    
    This shows how the frontend can use these functions to provide
    helpful guidance to users when enabling cluster-based planning.
    """
    
    workspace_name = "pnc_phones"
    state_abbr = "DC"
    
    print("=" * 70)
    print("CLUSTER VALIDATION DEMO FOR UI INTEGRATION")
    print("=" * 70)
    
    # 1. Get cluster information (call when user enables clustering checkbox)
    print("\n1️⃣  Getting cluster information...")
    print("-" * 70)
    cluster_info = get_cluster_info(workspace_name, state_abbr)
    
    if cluster_info and cluster_info["clustered_file_exists"]:
        print(f"✓ Clustered data found")
        print(f"  • Total sites: {cluster_info['total_sites']}")
        print(f"  • Number of clusters: {cluster_info['cluster_count']}")
        print(f"  • Recommended minimum crews: {cluster_info['recommended_min_crews']}")
        print(f"\n  Cluster distribution:")
        for cluster_id, size in sorted(cluster_info['cluster_sizes'].items()):
            percentage = (size / cluster_info['total_sites']) * 100
            print(f"    - Cluster {cluster_id}: {size} sites ({percentage:.1f}%)")
    else:
        print("✗ Clustered data not found")
    
    # 2. Show recommendation message (display in UI when clustering is enabled)
    print("\n2️⃣  Recommendation message for user...")
    print("-" * 70)
    recommendation = get_cluster_recommendation_message(workspace_name, state_abbr)
    print(recommendation)
    
    # 3. Validate crew allocation (call before executing plan)
    print("\n3️⃣  Validating crew allocation scenarios...")
    print("-" * 70)
    
    # Scenario A: Insufficient crews (3 crews for 4 clusters)
    print("\n📋 Scenario A: User requests 3 crews")
    validation = validate_cluster_crew_allocation(workspace_name, state_abbr, requested_crews=3)
    print(f"  • Valid: {validation['is_valid']}")
    print(f"  • Requested crews: {validation['requested_crews']}")
    print(f"  • Cluster count: {validation['cluster_count']}")
    print(f"  • Recommended crews: {validation['recommended_crews']}")
    print(f"  • Clusters skipped: {validation['clusters_skipped']}")
    print(f"  • Estimated unassigned sites: {validation['unassigned_sites_estimate']}")
    if validation['warning_message']:
        print(f"\n  ⚠️  {validation['warning_message']}")
    
    # Scenario B: Sufficient crews (4 crews for 4 clusters)
    print("\n📋 Scenario B: User requests 4 crews")
    validation = validate_cluster_crew_allocation(workspace_name, state_abbr, requested_crews=4)
    print(f"  • Valid: {validation['is_valid']}")
    print(f"  • Requested crews: {validation['requested_crews']}")
    print(f"  • Cluster count: {validation['cluster_count']}")
    print(f"  • Recommended crews: {validation['recommended_crews']}")
    print(f"  • Clusters skipped: {validation['clusters_skipped']}")
    print(f"  • Estimated unassigned sites: {validation['unassigned_sites_estimate']}")
    if validation['warning_message']:
        print(f"\n  ⚠️  {validation['warning_message']}")
    else:
        print(f"\n  ✓ All clusters will be planned")
    
    # Scenario C: More than enough crews (5 crews for 4 clusters)
    print("\n📋 Scenario C: User requests 5 crews")
    validation = validate_cluster_crew_allocation(workspace_name, state_abbr, requested_crews=5)
    print(f"  • Valid: {validation['is_valid']}")
    print(f"  • Requested crews: {validation['requested_crews']}")
    print(f"  • Cluster count: {validation['cluster_count']}")
    print(f"  • Recommended crews: {validation['recommended_crews']}")
    if validation['warning_message']:
        print(f"\n  ⚠️  {validation['warning_message']}")
    else:
        print(f"\n  ✓ All clusters will be planned (extra crews available)")
    
    print("\n" + "=" * 70)
    print("UI INTEGRATION RECOMMENDATIONS")
    print("=" * 70)
    print("""
1. When user enables clustering checkbox:
   → Call get_cluster_info() to get cluster count
   → Display cluster count and recommended crew count
   → Show get_cluster_recommendation_message()

2. Before user clicks "Plan Routes":
   → Call validate_cluster_crew_allocation()
   → Display info_message to user
   → Show estimated_days and planning_efficiency
   → Color code: green (optimal), yellow (good), orange (slow)

3. In the crew count input field:
   → Show recommended_crews as a hint/placeholder
   → Show estimated_days next to crew input
   → Highlight: green if optimal, yellow if good, orange if slow

4. After planning completes:
   → Show actual days used vs estimated
   → All sites will be planned with sequential cluster planning
   → Provide option to increase crews for faster completion
    """)


if __name__ == "__main__":
    demo_cluster_validation()
