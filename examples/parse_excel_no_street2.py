"""
Demo showing parse_excel with optional street2 field.
Some clients don't have a secondary address line, so street2 is optional.
"""
from planning_engine import new_workspace, parse_excel
import pandas as pd
from pathlib import Path

# Create a sample Excel file WITHOUT street2
print("Creating sample Excel file without street2...")
sample_data = pd.DataFrame({
    'SiteID': ['SITE_A', 'SITE_B', 'SITE_C'],
    'Address': ['123 Main Street', '456 Oak Avenue', '789 Pine Road'],
    'City': ['St Louis', 'Clayton', 'Webster Groves'],
    'State': ['MO', 'MO', 'MO'],
    'ZipCode': ['63101', '63105', '63119']
})

excel_file = Path("temp_no_street2.xlsx")
sample_data.to_excel(excel_file, index=False, engine='openpyxl')
print(f"✓ Excel file created: {excel_file}")
print(f"  Columns: {list(sample_data.columns)}")
print("  Note: No street2 column!")

# Create workspace
print("\nCreating workspace...")
workspace_path = new_workspace("no_street2_demo")
print(f"✓ Workspace created: {workspace_path}")

# Define column mapping WITHOUT street2
# This is valid because street2 is optional
column_mapping = {
    'site_id': 'SiteID',
    'street1': 'Address',
    # 'street2' is omitted - this is OK!
    'city': 'City',
    'state': 'State',
    'zip': 'ZipCode'
}

print("\nColumn Mapping (street2 omitted):")
for standard, custom in column_mapping.items():
    print(f"  {standard:12} <- {custom}")

# Parse Excel file
print("\nParsing Excel file...")
output_path = parse_excel(
    workspace_name="no_street2_demo",
    file_path=str(excel_file),
    column_mapping=column_mapping
)
print(f"✓ Parsing successful!")
print(f"  Output: {output_path}")

# Verify output
result_df = pd.read_csv(output_path)
print(f"\n✓ CSV contains {len(result_df)} rows")
print(f"  Columns: {list(result_df.columns)}")
print("\nData:")
print(result_df.to_string(index=False))

# Cleanup
excel_file.unlink()
print(f"\n✓ Cleaned up: {excel_file}")

print("\n" + "="*60)
print("SUCCESS! street2 is optional - parsing works without it.")
print("="*60)
