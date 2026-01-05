"""Test geocoding error handling - separating failed geocodes into error file."""

import pytest
import pandas as pd
from pathlib import Path
from planning_engine import new_workspace, parse_excel


def test_geocoding_errors_separated(tmp_path, monkeypatch):
    """Test that failed geocodes are written to geocoded-errors.csv."""
    # Change to temp directory for test
    monkeypatch.chdir(tmp_path)
    
    # Create workspace
    workspace_name = "test_geocode_errors"
    workspace_path = new_workspace(workspace_name)
    
    # Create test addresses CSV with some addresses
    state_dir = workspace_path / "input" / "PA"
    state_dir.mkdir(parents=True, exist_ok=True)
    
    addresses_csv = state_dir / "addresses.csv"
    df = pd.DataFrame({
        'street1': ['123 Main St', '456 Oak Ave', '789 Pine Rd'],
        'city': ['Philadelphia', 'Pittsburgh', 'Harrisburg'],
        'state': ['PA', 'PA', 'PA'],
        'zip': ['19019', '15201', '17101']
    })
    df.to_csv(addresses_csv, index=False)
    
    # Mock the batch_geocode_sites function to return some failures
    def mock_batch_geocode(addresses):
        """Mock geocoding that fails for the second address."""
        return [
            {'lat': 39.9526, 'lon': -75.1652},  # Success
            {},  # Failure - no lat/lon
            {'lat': 40.2732, 'lon': -76.8867}   # Success
        ]
    
    # Patch the geocoding function
    from planning_engine.data_prep import geocode as geocode_module
    monkeypatch.setattr(geocode_module, 'batch_geocode_sites', mock_batch_geocode)
    
    # Import after patching
    from planning_engine import geocode
    
    # Run geocoding - should raise ValueError due to errors
    with pytest.raises(ValueError) as exc_info:
        geocode(workspace_name, "PA")
    
    # Verify error message contains details
    assert "1 error(s)" in str(exc_info.value)
    assert "Successfully geocoded 2 addresses" in str(exc_info.value)
    
    # Verify geocoded.csv only has successful geocodes
    cache_dir = workspace_path / "cache" / "PA"
    geocoded_csv = cache_dir / "geocoded.csv"
    assert geocoded_csv.exists(), "geocoded.csv should exist"
    
    df_success = pd.read_csv(geocoded_csv)
    assert len(df_success) == 2, "Should have 2 successfully geocoded addresses"
    assert df_success['lat'].notna().all(), "All lat values should be valid"
    assert df_success['lon'].notna().all(), "All lon values should be valid"
    
    # Verify geocoded-errors.csv has the failed geocode
    error_csv = cache_dir / "geocoded-errors.csv"
    assert error_csv.exists(), "geocoded-errors.csv should exist"
    
    df_errors = pd.read_csv(error_csv)
    assert len(df_errors) == 1, "Should have 1 failed geocode"
    assert df_errors.iloc[0]['street1'] == '456 Oak Ave', "Failed address should be Oak Ave"
    assert pd.isna(df_errors.iloc[0]['lat']), "Failed geocode should have NaN lat"
    assert pd.isna(df_errors.iloc[0]['lon']), "Failed geocode should have NaN lon"


def test_geocoding_all_success_no_error_file(tmp_path, monkeypatch):
    """Test that no error file is created when all geocodes succeed."""
    # Change to temp directory for test
    monkeypatch.chdir(tmp_path)
    
    # Create workspace
    workspace_name = "test_geocode_success"
    workspace_path = new_workspace(workspace_name)
    
    # Create test addresses CSV
    state_dir = workspace_path / "input" / "TX"
    state_dir.mkdir(parents=True, exist_ok=True)
    
    addresses_csv = state_dir / "addresses.csv"
    df = pd.DataFrame({
        'street1': ['100 Congress Ave', '200 Lavaca St'],
        'city': ['Austin', 'Austin'],
        'state': ['TX', 'TX'],
        'zip': ['78701', '78701']
    })
    df.to_csv(addresses_csv, index=False)
    
    # Mock the batch_geocode_sites function to return all successes
    def mock_batch_geocode(addresses):
        """Mock geocoding that succeeds for all addresses."""
        return [
            {'lat': 30.2672, 'lon': -97.7431},
            {'lat': 30.2711, 'lon': -97.7437}
        ]
    
    # Patch the geocoding function
    from planning_engine.data_prep import geocode as geocode_module
    monkeypatch.setattr(geocode_module, 'batch_geocode_sites', mock_batch_geocode)
    
    # Import after patching
    from planning_engine import geocode
    
    # Run geocoding - should succeed without raising
    result_path = geocode(workspace_name, "TX")
    
    # Verify geocoded.csv has all addresses
    assert result_path.exists()
    df_result = pd.read_csv(result_path)
    assert len(df_result) == 2, "Should have 2 geocoded addresses"
    assert df_result['lat'].notna().all(), "All lat values should be valid"
    assert df_result['lon'].notna().all(), "All lon values should be valid"
    
    # Verify no error file was created
    cache_dir = workspace_path / "cache" / "TX"
    error_csv = cache_dir / "geocoded-errors.csv"
    assert not error_csv.exists(), "geocoded-errors.csv should NOT exist when all succeed"
