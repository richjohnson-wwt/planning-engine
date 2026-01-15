import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from typing import Tuple


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance between two points on earth in miles.
    
    Args:
        lat1, lon1: Coordinates of first point
        lat2, lon2: Coordinates of second point
        
    Returns:
        Distance in miles
    """
    # Convert to radians
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat/2)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2)**2
    c = 2 * np.arcsin(np.sqrt(a))
    
    # Radius of earth in miles
    r = 3959
    return c * r


def calculate_cluster_diameter(coordinates: np.ndarray) -> float:
    """
    Calculate the maximum distance between any two points in a cluster.
    
    Args:
        coordinates: Nx2 array of (lat, lon) coordinates
        
    Returns:
        Maximum distance in miles
    """
    if len(coordinates) <= 1:
        return 0.0
    
    max_distance = 0.0
    for i in range(len(coordinates)):
        for j in range(i + 1, len(coordinates)):
            dist = haversine_distance(
                coordinates[i, 0], coordinates[i, 1],
                coordinates[j, 0], coordinates[j, 1]
            )
            max_distance = max(max_distance, dist)
    
    return max_distance


def evaluate_clustering_quality(coordinates: np.ndarray, labels: np.ndarray, max_diameter_miles: float = 100) -> Tuple[float, float, int]:
    """
    Evaluate clustering quality based on silhouette score and cluster diameters.
    
    Args:
        coordinates: Nx2 array of (lat, lon) coordinates
        labels: Cluster labels for each point
        max_diameter_miles: Maximum allowed cluster diameter in miles
        
    Returns:
        Tuple of (combined_score, max_diameter, num_oversized_clusters)
    """
    # Calculate silhouette score
    if len(np.unique(labels)) > 1:
        silhouette = silhouette_score(coordinates, labels)
    else:
        silhouette = 0.0
    
    # Calculate cluster diameters
    max_diameter = 0.0
    oversized_clusters = 0
    
    for cluster_id in np.unique(labels):
        cluster_coords = coordinates[labels == cluster_id]
        diameter = calculate_cluster_diameter(cluster_coords)
        max_diameter = max(max_diameter, diameter)
        
        if diameter > max_diameter_miles:
            oversized_clusters += 1
    
    # Penalize oversized clusters heavily
    diameter_penalty = oversized_clusters * 0.3
    combined_score = silhouette - diameter_penalty
    
    return combined_score, max_diameter, oversized_clusters


def determine_optimal_k(coordinates: np.ndarray, max_k: int = 20, max_diameter_miles: float = 100) -> int:
    """
    Determine optimal number of clusters using silhouette score and geographic constraints.
    
    Args:
        coordinates: Nx2 array of (lat, lon) coordinates
        max_k: Maximum number of clusters to try
        max_diameter_miles: Maximum allowed cluster diameter in miles
        
    Returns:
        Optimal number of clusters
    """
    n_samples = len(coordinates)
    
    # Can't have more clusters than samples
    max_k = min(max_k, n_samples - 1)
    
    # Need at least 5 samples per cluster on average for meaningful clusters
    max_k = min(max_k, n_samples // 5)
    
    # Need at least 2 clusters for silhouette score
    if max_k < 2:
        return 1
    
    best_k = 2
    best_score = -1
    best_max_diameter = float('inf')
    
    print(f"  Evaluating cluster configurations (k=2 to k={max_k})...")
    
    # Try different k values and find the one with best combined score
    for k in range(2, max_k + 1):
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(coordinates)
        
        combined_score, max_diameter, oversized = evaluate_clustering_quality(
            coordinates, labels, max_diameter_miles
        )
        
        # Prefer configurations with no oversized clusters
        # If both have oversized clusters, prefer higher k (more granular)
        is_better = False
        if combined_score > best_score:
            is_better = True
        elif combined_score == best_score and max_diameter < best_max_diameter:
            is_better = True
        
        if is_better:
            best_score = combined_score
            best_k = k
            best_max_diameter = max_diameter
            
        if k <= 10 or oversized > 0:  # Show details for small k or problematic configs
            print(f"    k={k}: score={combined_score:.3f}, max_diameter={max_diameter:.1f}mi, oversized={oversized}")
    
    return best_k


def split_oversized_clusters(df: pd.DataFrame, max_diameter_miles: float = 100) -> pd.DataFrame:
    """
    Iteratively split clusters that exceed the maximum diameter constraint.
    
    Args:
        df: DataFrame with 'lat', 'lon', and 'cluster_id' columns
        max_diameter_miles: Maximum allowed cluster diameter in miles
        
    Returns:
        DataFrame with refined cluster_id assignments
    """
    max_iterations = 5
    iteration = 0
    next_cluster_id = df['cluster_id'].max() + 1
    
    while iteration < max_iterations:
        iteration += 1
        split_occurred = False
        
        for cluster_id in sorted(df['cluster_id'].unique()):
            if cluster_id < 0:  # Skip invalid clusters
                continue
                
            cluster_mask = df['cluster_id'] == cluster_id
            cluster_coords = df.loc[cluster_mask, ['lat', 'lon']].values
            
            if len(cluster_coords) < 2:
                continue
            
            diameter = calculate_cluster_diameter(cluster_coords)
            
            if diameter > max_diameter_miles:
                print(f"  Splitting cluster {cluster_id} (diameter: {diameter:.1f} miles, {len(cluster_coords)} sites)")
                
                # Split this cluster into 2 sub-clusters
                kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
                sub_labels = kmeans.fit_predict(cluster_coords)
                
                # Assign new cluster IDs
                cluster_indices = df[cluster_mask].index
                for idx, sub_label in zip(cluster_indices, sub_labels):
                    if sub_label == 1:
                        df.at[idx, 'cluster_id'] = next_cluster_id
                
                next_cluster_id += 1
                split_occurred = True
        
        if not split_occurred:
            break
    
    # Renumber clusters to be sequential starting from 0
    unique_clusters = sorted([c for c in df['cluster_id'].unique() if c >= 0])
    cluster_mapping = {old_id: new_id for new_id, old_id in enumerate(unique_clusters)}
    df['cluster_id'] = df['cluster_id'].map(lambda x: cluster_mapping.get(x, -1))
    
    return df


def cluster_sites(df: pd.DataFrame, max_diameter_miles: float = 100) -> pd.DataFrame:
    """
    Cluster sites based on their geographic coordinates with diameter constraints.
    
    Uses K-means clustering with automatic k determination, then iteratively splits
    clusters that exceed the maximum diameter constraint to ensure teams don't have
    to travel excessive distances within a cluster.
    
    Args:
        df: DataFrame with 'lat' and 'lon' columns
        max_diameter_miles: Maximum allowed cluster diameter in miles (default: 100)
        
    Returns:
        DataFrame with added 'cluster_id' column
        
    Raises:
        ValueError: If lat/lon columns are missing or contain invalid data
    """
    # Validate required columns
    if 'lat' not in df.columns or 'lon' not in df.columns:
        raise ValueError("DataFrame must contain 'lat' and 'lon' columns")
    
    # Remove rows with missing coordinates
    valid_coords = df[['lat', 'lon']].notna().all(axis=1)
    if not valid_coords.all():
        print(f"⚠ Warning: {(~valid_coords).sum()} sites have missing coordinates and will be assigned cluster -1")
    
    df_valid = df[valid_coords].copy()
    
    if len(df_valid) == 0:
        raise ValueError("No valid coordinates found for clustering")
    
    # Extract coordinates
    coordinates = df_valid[['lat', 'lon']].values
    
    # Determine optimal number of clusters with geographic constraints
    optimal_k = determine_optimal_k(coordinates, max_k=20, max_diameter_miles=max_diameter_miles)
    print(f"✓ Initial clustering with k={optimal_k}")
    
    # Perform initial clustering
    kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
    df_valid['cluster_id'] = kmeans.fit_predict(coordinates)
    
    # Initialize cluster_id column for all rows
    df['cluster_id'] = -1  # -1 for sites with missing coordinates
    df.loc[valid_coords, 'cluster_id'] = df_valid['cluster_id'].values
    
    # Split oversized clusters
    print(f"✓ Checking for oversized clusters (max diameter: {max_diameter_miles} miles)...")
    df = split_oversized_clusters(df, max_diameter_miles)
    
    # Print final cluster summary with diameters
    print(f"✓ Final cluster assignments:")
    for cluster_id in sorted(df[df['cluster_id'] >= 0]['cluster_id'].unique()):
        cluster_mask = df['cluster_id'] == cluster_id
        cluster_coords = df.loc[cluster_mask, ['lat', 'lon']].values
        count = len(cluster_coords)
        diameter = calculate_cluster_diameter(cluster_coords)
        print(f"  Cluster {cluster_id}: {count} sites (diameter: {diameter:.1f} miles)")
    
    return df