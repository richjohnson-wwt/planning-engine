from planning_engine import new_workspace, parse_excel
from pathlib import Path
import pytest
import pandas as pd
import shutil


def test_parse_excel_without_street2(tmp_path):
    """Test that street2 is optional - parsing works without it"""
    # Create test Excel file without street2 column
    test_data = pd.DataFrame({
        'Location': ['A', 'B', 'C'],
        'Street': ['123 Main St', '456 Oak Ave', '789 Pine Rd'],
        'Town': ['St Louis', 'Clayton', 'Webster Groves'],
        'ST': ['MO', 'MO', 'MO'],
        'Postal': ['63101', '63105', '63119']
    })
    excel_file = tmp_path / "test_sites.xlsx"
    test_data.to_excel(excel_file, index=False, engine='openpyxl')
    
    workspace_name = "test_no_street2"
    
    try:
        # Create workspace
        new_workspace(workspace_name)
        
        # Parse Excel file WITHOUT street2 in mapping
        output_path = parse_excel(
            workspace_name=workspace_name,
            file_path=str(excel_file),
            column_mapping={
                'site_id': 'Location',
                'street1': 'Street',
                # No street2 mapping - this should be OK
                'city': 'Town',
                'state': 'ST',
                'zip': 'Postal'
            }
        )
        
        # Verify output file exists
        assert output_path.exists()
        
        # Verify CSV content has only the mapped columns (no street2)
        result_df = pd.read_csv(output_path)
        assert len(result_df) == 3
        assert list(result_df.columns) == ['site_id', 'street1', 'city', 'state', 'zip']
        assert 'street2' not in result_df.columns
        assert result_df['site_id'].tolist() == ['A', 'B', 'C']
        
    finally:
        # Cleanup
        if Path("data/workspace").exists():
            shutil.rmtree(f"data/workspace/{workspace_name}", ignore_errors=True)


def test_parse_excel_with_street2(tmp_path):
    """Test that street2 can still be included when available"""
    # Create test Excel file with street2 column
    test_data = pd.DataFrame({
        'Location': ['A', 'B', 'C'],
        'Street': ['123 Main St', '456 Oak Ave', '789 Pine Rd'],
        'Street2': ['Apt 1', 'Suite 200', ''],
        'Town': ['St Louis', 'Clayton', 'Webster Groves'],
        'ST': ['MO', 'MO', 'MO'],
        'Postal': ['63101', '63105', '63119']
    })
    excel_file = tmp_path / "test_sites.xlsx"
    test_data.to_excel(excel_file, index=False, engine='openpyxl')
    
    workspace_name = "test_with_street2"
    
    try:
        # Create workspace
        new_workspace(workspace_name)
        
        # Parse Excel file WITH street2 in mapping
        output_path = parse_excel(
            workspace_name=workspace_name,
            file_path=str(excel_file),
            column_mapping={
                'site_id': 'Location',
                'street1': 'Street',
                'street2': 'Street2',  # Include optional street2
                'city': 'Town',
                'state': 'ST',
                'zip': 'Postal'
            }
        )
        
        # Verify output file exists
        assert output_path.exists()
        
        # Verify CSV content includes street2
        result_df = pd.read_csv(output_path)
        assert len(result_df) == 3
        assert list(result_df.columns) == ['site_id', 'street1', 'street2', 'city', 'state', 'zip']
        assert result_df['street2'].tolist()[0] == 'Apt 1'
        
    finally:
        # Cleanup
        if Path("data/workspace").exists():
            shutil.rmtree(f"data/workspace/{workspace_name}", ignore_errors=True)


def test_parse_excel_missing_required_field(tmp_path):
    """Test that parsing fails if a required field is missing"""
    # Create test Excel file
    test_data = pd.DataFrame({
        'Location': ['A', 'B'],
        'Street': ['123 Main St', '456 Oak Ave']
    })
    excel_file = tmp_path / "test_sites.xlsx"
    test_data.to_excel(excel_file, index=False, engine='openpyxl')
    
    workspace_name = "test_missing_required"
    
    try:
        # Create workspace
        new_workspace(workspace_name)
        
        # Try to parse with missing required fields (city, state, zip)
        with pytest.raises(ValueError, match="Missing required fields in column_mapping"):
            parse_excel(
                workspace_name=workspace_name,
                file_path=str(excel_file),
                column_mapping={
                    'site_id': 'Location',
                    'street1': 'Street'
                    # Missing: city, state, zip (required)
                    # street2 is optional, so it's OK to omit
                }
            )
        
    finally:
        # Cleanup
        if Path("data/workspace").exists():
            shutil.rmtree(f"data/workspace/{workspace_name}", ignore_errors=True)
