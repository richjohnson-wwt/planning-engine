"""
Demo script showing the complete workflow: parse Excel → geocode addresses.
"""
from planning_engine import new_workspace, parse_excel, geocode
import pandas as pd
from pathlib import Path

# Step 1: Create workspace
print("Step 1: Creating workspace...")
workspace_name = "geocode_demo_2025"
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

# Show what we're about to geocode
df_addresses = pd.read_csv(addresses_csv)
print(f"\nAddresses to geocode: {len(df_addresses)} sites")
print("\nFirst 3 addresses:")
print(df_addresses[['site_id', 'street1', 'city', 'state', 'zip']].head(3).to_string(index=False))

# Step 3: Geocode the addresses
print("\n" + "="*60)
print("Step 3: Geocoding addresses...")
print("="*60)

try:
    geocoded_csv = geocode(workspace_name=workspace_name)
    print(f"\n✓ Geocoding complete: {geocoded_csv}")
    
    # Show the results
    df_geocoded = pd.read_csv(geocoded_csv)
    print(f"\nGeocoded {len(df_geocoded)} addresses")
    print("\nFirst 3 geocoded results:")
    print(df_geocoded[['site_id', 'street1', 'city', 'lat', 'lon']].head(3).to_string(index=False))
    
    # Check for any failed geocodes
    failed = df_geocoded[df_geocoded['lat'].isna()]
    if len(failed) > 0:
        print(f"\n⚠ Warning: {len(failed)} addresses failed to geocode")
    else:
        print(f"\n✓ All {len(df_geocoded)} addresses geocoded successfully!")
    
    print("\n" + "="*60)
    print("Demo complete!")
    print(f"Workspace: {workspace_path}")
    print(f"Addresses CSV: {addresses_csv}")
    print(f"Geocoded CSV: {geocoded_csv}")
    print("="*60)
    
except Exception as e:
    print(f"\n✗ Geocoding failed: {e}")
    print("\nNote: This demo requires a valid geoapify.com API key and internet connection.")
