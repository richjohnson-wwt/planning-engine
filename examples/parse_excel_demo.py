"""
Demo script showing how to use the parse_excel functionality with acme.xlsx.
This demonstrates mapping client-specific column names to standardized fields.
"""
from planning_engine import new_workspace, parse_excel
import pandas as pd
from pathlib import Path

# Step 1: Create a workspace
print("Creating workspace...")
workspace_path = new_workspace("acme_demo_2025")
print(f"✓ Workspace created at: {workspace_path}")

# Step 2: Define the Excel file path
excel_file = Path("examples/acme.xlsx")
print(f"\nUsing Excel file: {excel_file}")

# Check what columns are in the file
df_preview = pd.read_excel(excel_file, engine='openpyxl')
print(f"  Excel columns: {list(df_preview.columns)}")
print(f"  Total rows: {len(df_preview)}")
print("\nFirst 3 rows:")
print(df_preview.head(3).to_string(index=False))

# Step 3: Define column mapping
# Map our standard field names to ACME's custom column names
column_mapping = {
    'site_id': 'Location',      # ACME uses "Location" for site IDs
    'street1': 'MyStreet1',     # ACME uses "MyStreet1" for primary address
    'street2': 'MyStreet2',     # ACME uses "MyStreet2" for secondary address
    'city': 'MyCity',           # ACME uses "MyCity" for city
    'state': 'MyState',         # ACME uses "MyState" for state
    'zip': 'MyZip'              # ACME uses "MyZip" for zip code
}

print("\n" + "="*60)
print("Column Mapping:")
for standard, custom in column_mapping.items():
    print(f"  {standard:12} <- {custom}")

# Step 4: Parse Excel file with column mapping
print("\n" + "="*60)
print("Parsing Excel file with column mapping...")
output_path = parse_excel(
    workspace_name="acme_demo_2025",
    file_path=str(excel_file),
    column_mapping=column_mapping
)
print(f"✓ Excel parsed successfully!")
print(f"  Output saved to: {output_path}")

# Step 5: Verify the output
print("\nVerifying output CSV...")
result_df = pd.read_csv(output_path)
print(f"✓ CSV contains {len(result_df)} rows")
print(f"  Standardized columns: {list(result_df.columns)}")
print("\nFirst 5 rows of standardized data:")
print(result_df.head(5).to_string(index=False))

print("\n" + "="*60)
print("Demo complete! The Excel data has been:")
print("  1. Parsed from ACME's custom format")
print("  2. Mapped to standardized field names")
print("  3. Saved as CSV for further processing")
print(f"\nWorkspace location: {workspace_path}")
print(f"Output CSV: {output_path}")
