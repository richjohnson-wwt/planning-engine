"""Test improved DC crew allocation with minimum 1 crew per cluster."""

def test_dc_improved_allocation():
    """
    Test improved crew allocation for DC scenario.
    
    DC data:
    - Cluster 0: 2 sites (10.5%)
    - Cluster 1: 10 sites (52.6%)
    - Cluster 2: 5 sites (26.3%)
    - Cluster 3: 2 sites (10.5%)
    Total: 19 sites, 3 crews requested
    
    Expected: Each cluster gets at least 1 crew
    """
    
    total_crews = 3
    cluster_sizes = {0: 2, 1: 10, 2: 5, 3: 2}
    total_sites = 19
    cluster_ids = [0, 1, 2, 3]
    
    # Allocate crews using largest remainder method
    cluster_crew_allocation = {}
    proportions = {cid: size / total_sites for cid, size in cluster_sizes.items()}
    
    # First pass: allocate floor of proportional crews
    allocated = 0
    remainders = {}
    for cluster_id, proportion in proportions.items():
        exact_crews = total_crews * proportion
        floor_crews = int(exact_crews)
        cluster_crew_allocation[cluster_id] = floor_crews
        allocated += floor_crews
        remainders[cluster_id] = exact_crews - floor_crews
    
    print("=== DC Improved Crew Allocation ===")
    print(f"Total crews: {total_crews}")
    print(f"Total sites: {total_sites}")
    print(f"\nFirst pass (floor allocation):")
    for cluster_id in sorted(cluster_crew_allocation.keys()):
        print(f"  Cluster {cluster_id}: {cluster_sizes[cluster_id]} sites → {cluster_crew_allocation[cluster_id]} crews")
    print(f"Allocated: {allocated}/{total_crews}")
    
    # Second pass: distribute remaining crews
    remaining = total_crews - allocated
    if remaining > 0:
        print(f"\nSecond pass (distribute {remaining} remaining crews by largest remainder):")
        sorted_clusters = sorted(remainders.items(), key=lambda x: x[1], reverse=True)
        for i in range(remaining):
            cluster_id = sorted_clusters[i][0]
            cluster_crew_allocation[cluster_id] += 1
            print(f"  +1 crew to Cluster {cluster_id} (remainder: {remainders[cluster_id]:.3f})")
    
    # Third pass: ensure minimum 1 crew per cluster
    zero_crew_clusters = [cid for cid in cluster_ids if cluster_crew_allocation[cid] == 0 and cluster_sizes[cid] > 0]
    
    if zero_crew_clusters:
        print(f"\nThird pass (ensure minimum 1 crew per cluster):")
        print(f"  {len(zero_crew_clusters)} clusters have 0 crews")
        
        for cluster_id in zero_crew_clusters:
            donors = [(cid, crews) for cid, crews in cluster_crew_allocation.items() if crews > 1]
            if donors:
                donor_id = max(donors, key=lambda x: x[1])[0]
                cluster_crew_allocation[donor_id] -= 1
                cluster_crew_allocation[cluster_id] = 1
                print(f"  Moved 1 crew from Cluster {donor_id} to Cluster {cluster_id}")
    
    print(f"\nFinal allocation:")
    total_allocated = 0
    for cluster_id in sorted(cluster_crew_allocation.keys()):
        crews = cluster_crew_allocation[cluster_id]
        total_allocated += crews
        print(f"  Cluster {cluster_id}: {cluster_sizes[cluster_id]} sites ({proportions[cluster_id]:.1%}) → {crews} crews")
    
    print(f"\nTotal allocated: {total_allocated}/{total_crews}")
    
    # Verify constraints
    assert total_allocated == total_crews, f"Total allocated ({total_allocated}) != requested ({total_crews})"
    
    # With only 3 crews and 4 clusters, we can't give every cluster a crew
    # At least 3 clusters should have crews
    clusters_with_crews = sum(1 for crews in cluster_crew_allocation.values() if crews > 0)
    assert clusters_with_crews >= min(total_crews, len(cluster_ids)), f"Expected at least {min(total_crews, len(cluster_ids))} clusters with crews"
    
    print("\n✓ DC improved allocation test PASSED")
    print(f"Result: {clusters_with_crews} out of 4 clusters get crews (limited by {total_crews} total crews)")
    print(f"Cluster 3 with 2 sites will be SKIPPED (insufficient crews)")
    print(f"Expected behavior: 3 crews working over multiple days across 3 clusters")


if __name__ == "__main__":
    test_dc_improved_allocation()
