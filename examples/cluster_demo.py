"""
Demo script showing the complete workflow: parse Excel → geocode → cluster.
"""
from planning_engine import new_workspace, parse_excel, geocode, cluster
import pandas as pd
from pathlib import Path

# Step 1: Create workspace
print("Step 1: Creating workspace...")
workspace_name = "cluster_demo_2025"
workspace_path = new_workspace(workspace_name)
print(f"✓ Workspace created: {workspace_path}")

# Step 2: Parse Excel file with column mapping
print("\nStep 2: Parsing Excel file...")
excel_file = Path("examples/acme.xlsx")

column_mapping = {
    'site_id': 'Location',
    'street1': 'MyStreet1',
    'street2': 'MyStreet2',
    'city': 'MyCity',
    'state': 'MyState',
    'zip': 'MyZip'
}

addresses_csv = parse_excel(
    workspace_name=workspace_name,
    file_path=str(excel_file),
    column_mapping=column_mapping
)
print(f"✓ Addresses parsed: {addresses_csv}")

# Step 3: Geocode the addresses
print("\n" + "="*60)
print("Step 3: Geocoding addresses...")
print("="*60)

try:
    state_abbr='LA'
    geocoded_csv = geocode(workspace_name=workspace_name, state_abbr=state_abbr)
    print(f"\n✓ Geocoding complete: {geocoded_csv}")
    
    # Show geocoded results
    df_geocoded = pd.read_csv(geocoded_csv)
    print(f"\nGeocoded {len(df_geocoded)} addresses")
    
    # Step 4: Cluster the sites
    print("\n" + "="*60)
    print("Step 4: Clustering sites...")
    print("="*60)
    
    clustered_csv = cluster(workspace_name=workspace_name, state_abbr=state_abbr)
    print(f"\n✓ Clustering complete: {clustered_csv}")
    
    # Show clustering results
    df_clustered = pd.read_csv(clustered_csv)
    print(f"\nClustered {len(df_clustered)} sites")
    print("\nCluster distribution:")
    cluster_summary = df_clustered[df_clustered['cluster_id'] >= 0].groupby('cluster_id').agg({
        'site_id': 'count',
        'city': lambda x: ', '.join(x.unique()[:3])  # Show up to 3 unique cities
    }).rename(columns={'site_id': 'count', 'city': 'cities'})
    print(cluster_summary.to_string())
    
    print("\n" + "="*60)
    print("Demo complete! Full pipeline executed:")
    print(f"  1. Parsed Excel → {addresses_csv}")
    print(f"  2. Geocoded addresses → {geocoded_csv}")
    print(f"  3. Clustered sites → {clustered_csv}")
    print("="*60)
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    print("\nNote: This demo requires a valid Geoapify API key and internet connection.")
