from planning_engine import new_workspace, parse_excel
from pathlib import Path
import pytest
import pandas as pd
import shutil


def test_parse_excel_with_mapping(tmp_path):
    """Test that parsing fails if workspace doesn't exist"""
    # Create test Excel file
    test_data = pd.DataFrame({
        'Location': ['A'],
        'Street': ['123 Main St'],
        'Street2': [''],
        'Town': ['St Louis'],
        'ST': ['MO'],
        'Postal': ['63101']
    })
    excel_file = tmp_path / "test_sites.xlsx"
    test_data.to_excel(excel_file, index=False, engine='openpyxl')
    
    # Try to parse without creating workspace first
    with pytest.raises(FileNotFoundError, match="Workspace 'nonexistent' does not exist"):
        parse_excel(
            workspace_name="nonexistent",
            file_path=str(excel_file),
            column_mapping={
                'site_id': 'Location',
                'street1': 'Street',
                'street2': 'Street2',
                'city': 'Town',
                'state': 'ST',
                'zip': 'Postal'
            }
        )


def test_parse_excel_file_not_found():
    """Test that parsing fails if Excel file doesn't exist"""
    workspace_name = "test_file_not_found"
    
    try:
        # Create workspace
        new_workspace(workspace_name)
        
        # Try to parse non-existent file
        with pytest.raises(FileNotFoundError, match="Excel file not found"):
            parse_excel(
                workspace_name=workspace_name,
                file_path="nonexistent.xlsx",
                column_mapping={
                    'site_id': 'Location',
                    'street1': 'Street',
                    'street2': 'Street2',
                    'city': 'Town',
                    'state': 'ST',
                    'zip': 'Postal'
                }
            )
            
    finally:
        # Cleanup
        if Path("data/workspace").exists():
            shutil.rmtree(f"data/workspace/{workspace_name}", ignore_errors=True)


def test_parse_excel_overwrites_existing(tmp_path):
    """Test that parsing overwrites existing addresses.csv"""
    # Create test Excel files with required columns
    test_data1 = pd.DataFrame({
        'Location': ['A'],
        'Street': ['123 Main'],
        'Street2': [''],
        'Town': ['St Louis'],
        'ST': ['MO'],
        'Postal': ['63101']
    })
    excel_file1 = tmp_path / "test1.xlsx"
    test_data1.to_excel(excel_file1, index=False, engine='openpyxl')
    
    test_data2 = pd.DataFrame({
        'Location': ['B', 'C'],
        'Street': ['456 Oak', '789 Pine'],
        'Street2': ['', ''],
        'Town': ['Clayton', 'Webster'],
        'ST': ['MO', 'MO'],
        'Postal': ['63105', '63119']
    })
    excel_file2 = tmp_path / "test2.xlsx"
    test_data2.to_excel(excel_file2, index=False, engine='openpyxl')
    
    workspace_name = "test_overwrite"
    
    column_mapping = {
        'site_id': 'Location',
        'street1': 'Street',
        'street2': 'Street2',
        'city': 'Town',
        'state': 'ST',
        'zip': 'Postal'
    }
    
    try:
        # Create workspace
        new_workspace(workspace_name)
        
        # Parse first file
        output_path1 = parse_excel(workspace_name, str(excel_file1), column_mapping)
        result1 = pd.read_csv(output_path1)
        assert len(result1) == 1
        
        # Parse second file (should overwrite)
        output_path2 = parse_excel(workspace_name, str(excel_file2), column_mapping)
        result2 = pd.read_csv(output_path2)
        assert len(result2) == 2
        assert result2['site_id'].tolist() == ['B', 'C']
        
    finally:
        # Cleanup
        if Path("data/workspace").exists():
            shutil.rmtree(f"data/workspace/{workspace_name}", ignore_errors=True)
