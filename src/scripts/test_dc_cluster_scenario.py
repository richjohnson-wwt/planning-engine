"""Test DC scenario: 19 sites in 4 clusters with 3 crews."""

def test_dc_crew_allocation():
    """
    Test crew allocation for DC scenario.
    
    DC data:
    - Cluster 0: 2 sites (10.5%)
    - Cluster 1: 10 sites (52.6%)
    - Cluster 2: 5 sites (26.3%)
    - Cluster 3: 2 sites (10.5%)
    Total: 19 sites, 3 crews requested
    """
    
    total_crews = 3
    cluster_sizes = {0: 2, 1: 10, 2: 5, 3: 2}
    total_sites = 19
    
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
    
    print("=== DC Cluster Crew Allocation ===")
    print(f"Total crews: {total_crews}")
    print(f"Total sites: {total_sites}")
    print(f"\nFirst pass (floor allocation):")
    for cluster_id in sorted(cluster_crew_allocation.keys()):
        print(f"  Cluster {cluster_id}: {cluster_sizes[cluster_id]} sites → {cluster_crew_allocation[cluster_id]} crews (remainder: {remainders[cluster_id]:.3f})")
    print(f"Allocated: {allocated}/{total_crews}")
    
    # Second pass: distribute remaining crews to clusters with largest remainders
    remaining = total_crews - allocated
    if remaining > 0:
        print(f"\nSecond pass (distribute {remaining} remaining crews):")
        sorted_clusters = sorted(remainders.items(), key=lambda x: x[1], reverse=True)
        for i in range(remaining):
            cluster_id = sorted_clusters[i][0]
            cluster_crew_allocation[cluster_id] += 1
            print(f"  +1 crew to Cluster {cluster_id} (had largest remainder: {remainders[cluster_id]:.3f})")
    
    print(f"\nFinal allocation:")
    total_allocated = 0
    for cluster_id in sorted(cluster_crew_allocation.keys()):
        crews = cluster_crew_allocation[cluster_id]
        total_allocated += crews
        print(f"  Cluster {cluster_id}: {cluster_sizes[cluster_id]} sites ({proportions[cluster_id]:.1%}) → {crews} crews")
    
    print(f"\nTotal allocated: {total_allocated}/{total_crews}")
    
    # Verify constraints
    assert total_allocated == total_crews, f"Total allocated ({total_allocated}) != requested ({total_crews})"
    assert all(crews >= 0 for crews in cluster_crew_allocation.values()), "All clusters should have non-negative crews"
    
    # Expected allocation:
    # Cluster 0: 2/19 = 0.316 → floor=0, remainder=0.316
    # Cluster 1: 10/19 = 1.579 → floor=1, remainder=0.579 (largest)
    # Cluster 2: 5/19 = 0.789 → floor=0, remainder=0.789 (2nd largest)
    # Cluster 3: 2/19 = 0.316 → floor=0, remainder=0.316
    # After distributing 3 remaining: Cluster 2 gets +1, Cluster 1 gets +1, Cluster 0 or 3 gets +1
    
    print("\n✓ DC crew allocation test PASSED")
    print(f"Expected result: 3 crews distributed across 4 clusters")
    print(f"Clusters will work over multiple days as needed")


if __name__ == "__main__":
    test_dc_crew_allocation()
