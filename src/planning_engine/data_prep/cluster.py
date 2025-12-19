import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score


def determine_optimal_k(coordinates: np.ndarray, max_k: int = 10) -> int:
    """
    Determine optimal number of clusters using silhouette score.
    
    Args:
        coordinates: Nx2 array of (lat, lon) coordinates
        max_k: Maximum number of clusters to try
        
    Returns:
        Optimal number of clusters
    """
    n_samples = len(coordinates)
    
    # Can't have more clusters than samples
    max_k = min(max_k, n_samples - 1)
    
    # Need at least 2 samples per cluster on average
    max_k = min(max_k, n_samples // 2)
    
    # Need at least 2 clusters for silhouette score
    if max_k < 2:
        return 1
    
    best_k = 2
    best_score = -1
    
    # Try different k values and find the one with best silhouette score
    for k in range(2, max_k + 1):
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(coordinates)
        score = silhouette_score(coordinates, labels)
        
        if score > best_score:
            best_score = score
            best_k = k
    
    return best_k


def cluster_sites(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cluster sites based on their geographic coordinates using auto-k determination.
    
    Args:
        df: DataFrame with 'lat' and 'lon' columns
        
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
    
    # Determine optimal number of clusters
    optimal_k = determine_optimal_k(coordinates)
    print(f"✓ Optimal number of clusters determined: {optimal_k}")
    
    # Perform clustering
    kmeans = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
    df_valid['cluster_id'] = kmeans.fit_predict(coordinates)
    
    # Initialize cluster_id column for all rows
    df['cluster_id'] = -1  # -1 for sites with missing coordinates
    df.loc[valid_coords, 'cluster_id'] = df_valid['cluster_id'].values
    
    # Print cluster summary
    cluster_counts = df[df['cluster_id'] >= 0]['cluster_id'].value_counts().sort_index()
    print(f"✓ Sites assigned to {optimal_k} clusters:")
    for cluster_id, count in cluster_counts.items():
        print(f"  Cluster {cluster_id}: {count} sites")
    
    return df