"""
Tests for team schedule generation functionality.

Tests cover schedule generation with the new team structure where
team_id is a simple sequential ID and assigned_clusters contains
the cluster-team assignments.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import json
from datetime import date, datetime

from planning_engine.team_schedule import (
    load_team_info, _prepare_team_schedule_data,
    generate_team_schedule_pdf, generate_team_schedule_text
)
from planning_engine.models import Team
from planning_engine.team_management import add_team
from planning_engine import new_workspace


@pytest.fixture
def temp_workspace_with_plan():
    """Create a temporary workspace with planning results and teams."""
    # Create a unique workspace name to avoid conflicts
    workspace_name = f"test_workspace_{tempfile.mkdtemp().split('/')[-1]}"
    
    # Create workspace using new_workspace (creates in default data/workspace location)
    workspace_path = new_workspace(workspace_name)
    
    # Create cache directory for state
    cache_dir = workspace_path / "cache" / "GA"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    # Create output directory
    output_dir = workspace_path / "output" / "GA"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a mock planning result
    plan_result = {
        "metadata": {
            "workspace": workspace_name,
            "state_abbr": "GA",
            "timestamp": datetime.now().isoformat(),
            "max_route_minutes": 480
        },
        "result": {
            "team_days": [
                {
                    "team_id": 1,
                    "team_label": "C1-T1",
                    "date": "2026-01-15",
                    "route_day": 1,
                    "route_sequence": 1,
                    "route_id": "route_1",
                    "service_minutes": 240,
                    "travel_minutes": 30,
                    "sites": [
                        {
                            "id": "SITE001",
                            "name": "Test Site 1",
                            "address": "123 Main St",
                            "city": "Atlanta",
                            "state": "GA",
                            "zip": "30301",
                            "service_minutes": 120,
                            "travel_minutes": 15,
                            "contact_name": "John Doe",
                            "contact_phone": "555-1234"
                        },
                        {
                            "id": "SITE002",
                            "name": "Test Site 2",
                            "address": "456 Oak Ave",
                            "city": "Atlanta",
                            "state": "GA",
                            "zip": "30302",
                            "service_minutes": 120,
                            "travel_minutes": 15
                        }
                    ],
                    "site_ids": ["SITE001", "SITE002"]
                },
                {
                    "team_id": 2,
                    "team_label": "C1-T2",
                    "date": "2026-01-15",
                    "route_day": 1,
                    "route_sequence": 1,
                    "route_id": "route_2",
                    "service_minutes": 120,
                    "travel_minutes": 20,
                    "sites": [
                        {
                            "id": "SITE003",
                            "name": "Test Site 3",
                            "address": "789 Pine Rd",
                            "city": "Atlanta",
                            "state": "GA",
                            "zip": "30303",
                            "service_minutes": 120,
                            "travel_minutes": 20
                        }
                    ],
                    "site_ids": ["SITE003"]
                },
                {
                    "team_id": 3,
                    "team_label": "C1-T3",
                    "date": "2026-01-16",
                    "route_day": 2,
                    "route_sequence": 1,
                    "route_id": "route_3",
                    "service_minutes": 180,
                    "travel_minutes": 25,
                    "sites": [
                        {
                            "id": "SITE004",
                            "name": "Test Site 4",
                            "address": "321 Elm St",
                            "city": "Atlanta",
                            "state": "GA",
                            "zip": "30304",
                            "service_minutes": 180,
                            "travel_minutes": 25
                        }
                    ],
                    "site_ids": ["SITE004"]
                }
            ]
        }
    }
    
    # Save planning result
    plan_file = output_dir / f"route_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(plan_file, 'w') as f:
        json.dump(plan_result, f)
    
    # Create teams with new structure
    teams_csv_path = cache_dir / "teams.csv"
    
    # Team 1: Handles C1-T1 and C1-T2
    team1 = Team(
        team_id="1",
        team_name="North Team",
        city="Atlanta",
        assigned_clusters="C1-T1,C1-T2",
        contact_name="Alice Smith",
        contact_phone="555-1111",
        contact_email="alice@example.com",
        created_date=date.today()
    )
    
    # Team 2: Handles C1-T3
    team2 = Team(
        team_id="2",
        team_name="South Team",
        city="Atlanta",
        assigned_clusters="C1-T3",
        contact_name="Bob Jones",
        contact_phone="555-2222",
        contact_email="bob@example.com",
        created_date=date.today()
    )
    
    add_team(workspace_name, "GA", team1)
    add_team(workspace_name, "GA", team2)
    
    yield workspace_name, str(workspace_path.parent)
    
    # Cleanup
    shutil.rmtree(workspace_path, ignore_errors=True)


def test_load_team_info_with_simple_id(temp_workspace_with_plan):
    """Test loading team info using simple team_id."""
    workspace_name, temp_dir = temp_workspace_with_plan
    
    # WHEN: Loading team by simple ID "1"
    team = load_team_info(workspace_name, "GA", "1")
    
    # THEN: Should load team successfully
    assert team is not None
    assert team.team_id == "1"
    assert team.team_name == "North Team"
    assert team.assigned_clusters == "C1-T1,C1-T2"


def test_prepare_schedule_data_with_assigned_clusters(temp_workspace_with_plan):
    """Test that _prepare_team_schedule_data uses assigned_clusters to filter routes."""
    workspace_name, temp_dir = temp_workspace_with_plan
    
    # WHEN: Preparing schedule data for team "1" (assigned C1-T1 and C1-T2)
    schedule_data = _prepare_team_schedule_data(workspace_name, "GA", "1")
    
    # THEN: Should return data with routes for both C1-T1 and C1-T2
    assert schedule_data is not None
    assert schedule_data['team_info'].team_id == "1"
    assert schedule_data['team_info'].assigned_clusters == "C1-T1,C1-T2"
    
    # Should have 2 routes (C1-T1 and C1-T2)
    team_routes = schedule_data['team_routes']
    assert len(team_routes) == 2
    
    # Verify route labels
    route_labels = {route['team_label'] for route in team_routes}
    assert route_labels == {"C1-T1", "C1-T2"}


def test_prepare_schedule_data_single_cluster(temp_workspace_with_plan):
    """Test schedule data preparation for team with single cluster assignment."""
    workspace_name, temp_dir = temp_workspace_with_plan
    
    # WHEN: Preparing schedule data for team "2" (assigned only C1-T3)
    schedule_data = _prepare_team_schedule_data(workspace_name, "GA", "2")
    
    # THEN: Should return data with only C1-T3 route
    assert schedule_data is not None
    assert schedule_data['team_info'].team_id == "2"
    assert schedule_data['team_info'].assigned_clusters == "C1-T3"
    
    # Should have 1 route
    team_routes = schedule_data['team_routes']
    assert len(team_routes) == 1
    assert team_routes[0]['team_label'] == "C1-T3"


def test_generate_pdf_schedule_with_simple_id(temp_workspace_with_plan):
    """Test PDF generation using simple team_id."""
    workspace_name, temp_dir = temp_workspace_with_plan
    
    # GIVEN: Output path for PDF
    output_path = Path(temp_dir) / "schedule_team1.pdf"
    
    # WHEN: Generating PDF for team "1"
    success = generate_team_schedule_pdf(workspace_name, "GA", "1", output_path)
    
    # THEN: Should generate successfully
    assert success is True
    assert output_path.exists()
    assert output_path.stat().st_size > 0


def test_generate_text_schedule_with_simple_id(temp_workspace_with_plan):
    """Test text generation using simple team_id."""
    workspace_name, temp_dir = temp_workspace_with_plan
    
    # GIVEN: Output path for text file
    output_path = Path(temp_dir) / "schedule_team1.txt"
    
    # WHEN: Generating text schedule for team "1"
    success = generate_team_schedule_text(workspace_name, "GA", "1", output_path)
    
    # THEN: Should generate successfully
    assert success is True
    assert output_path.exists()
    
    # AND: Should contain team info and routes
    content = output_path.read_text()
    assert "Team ID:        1" in content
    assert "North Team" in content
    assert "ROUTE 1" in content
    assert "ROUTE 2" in content  # Should have 2 routes (C1-T1 and C1-T2)


def test_schedule_generation_with_no_assigned_clusters(temp_workspace_with_plan):
    """Test schedule generation for team with no assigned clusters."""
    workspace_name, temp_dir = temp_workspace_with_plan
    
    # GIVEN: A team with no assigned clusters
    from planning_engine.team_management import add_team
    team3 = Team(
        team_id="3",
        team_name="Unassigned Team",
        city="Atlanta",
        assigned_clusters=None,
        created_date=date.today()
    )
    add_team(workspace_name, "GA", team3)
    
    # WHEN: Trying to prepare schedule data
    schedule_data = _prepare_team_schedule_data(workspace_name, "GA", "3")
    
    # THEN: Should return None (no routes found)
    assert schedule_data is None


def test_schedule_includes_all_sites_from_assigned_clusters(temp_workspace_with_plan):
    """Test that schedule includes all sites from assigned cluster-teams."""
    workspace_name, temp_dir = temp_workspace_with_plan
    
    # WHEN: Preparing schedule for team "1" (C1-T1 and C1-T2)
    schedule_data = _prepare_team_schedule_data(workspace_name, "GA", "1")
    
    # THEN: Should include sites from both routes
    team_routes = schedule_data['team_routes']
    
    all_site_ids = []
    for route in team_routes:
        all_site_ids.extend(route['site_ids'])
    
    # Team 1 should have sites from C1-T1 (SITE001, SITE002) and C1-T2 (SITE003)
    assert set(all_site_ids) == {"SITE001", "SITE002", "SITE003"}


def test_schedule_excludes_sites_from_unassigned_clusters(temp_workspace_with_plan):
    """Test that schedule excludes sites from cluster-teams not assigned to the team."""
    workspace_name, temp_dir = temp_workspace_with_plan
    
    # WHEN: Preparing schedule for team "2" (only C1-T3)
    schedule_data = _prepare_team_schedule_data(workspace_name, "GA", "2")
    
    # THEN: Should only include sites from C1-T3
    team_routes = schedule_data['team_routes']
    
    all_site_ids = []
    for route in team_routes:
        all_site_ids.extend(route['site_ids'])
    
    # Team 2 should only have SITE004 from C1-T3
    assert set(all_site_ids) == {"SITE004"}
    
    # Should NOT include sites from C1-T1 or C1-T2
    assert "SITE001" not in all_site_ids
    assert "SITE002" not in all_site_ids
    assert "SITE003" not in all_site_ids


def test_nonexistent_team_returns_none(temp_workspace_with_plan):
    """Test that preparing schedule for non-existent team returns None."""
    workspace_name, temp_dir = temp_workspace_with_plan
    
    # WHEN: Trying to prepare schedule for non-existent team "999"
    schedule_data = _prepare_team_schedule_data(workspace_name, "GA", "999")
    
    # THEN: Should return None
    assert schedule_data is None


def test_team_with_clusters_not_in_plan(temp_workspace_with_plan):
    """Test team assigned to clusters that don't exist in planning result."""
    workspace_name, temp_dir = temp_workspace_with_plan
    
    # GIVEN: A team assigned to non-existent clusters
    from planning_engine.team_management import add_team
    team4 = Team(
        team_id="4",
        team_name="Ghost Team",
        city="Atlanta",
        assigned_clusters="C99-T99",  # Doesn't exist in plan
        created_date=date.today()
    )
    add_team(workspace_name, "GA", team4)
    
    # WHEN: Trying to prepare schedule data
    schedule_data = _prepare_team_schedule_data(workspace_name, "GA", "4")
    
    # THEN: Should return None (no matching routes)
    assert schedule_data is None
