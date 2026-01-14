"""
Tests for team management functionality.

Tests cover CRUD operations, team ID generation, and the new team structure
where team_id is a simple sequential ID and assigned_clusters contains
the cluster-team assignments.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from datetime import date

from planning_engine.team_management import (
    load_teams, save_teams, add_team, update_team, delete_team,
    generate_team_id, get_available_cities
)
from planning_engine.models import Team
from planning_engine import new_workspace


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    # Create a unique workspace name to avoid conflicts
    workspace_name = f"test_workspace_{tempfile.mkdtemp().split('/')[-1]}"
    
    # Create workspace using new_workspace (creates in default data/workspace location)
    workspace_path = new_workspace(workspace_name)
    
    # Create cache directory for state
    cache_dir = workspace_path / "cache" / "GA"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    yield workspace_name, str(workspace_path.parent)
    
    # Cleanup
    shutil.rmtree(workspace_path, ignore_errors=True)


def test_generate_team_id_creates_sequential_ids(temp_workspace):
    """Test that generate_team_id creates simple sequential IDs (1, 2, 3, etc)."""
    workspace_name, temp_dir = temp_workspace
    
    # GIVEN: No existing teams
    # WHEN: Generating first team ID
    team_id_1 = generate_team_id(workspace_name, "GA")
    
    # THEN: Should get "1"
    assert team_id_1 == "1"
    
    # GIVEN: One team exists with ID "1"
    team1 = Team(
        team_id="1",
        team_name="Team Alpha",
        city="Atlanta",
        assigned_clusters="C1-T1,C1-T2",
        created_date=date.today()
    )
    add_team(workspace_name, "GA", team1)
    
    # WHEN: Generating second team ID
    team_id_2 = generate_team_id(workspace_name, "GA")
    
    # THEN: Should get "2"
    assert team_id_2 == "2"
    
    # GIVEN: Two teams exist
    team2 = Team(
        team_id="2",
        team_name="Team Beta",
        city="Atlanta",
        assigned_clusters="C1-T3",
        created_date=date.today()
    )
    add_team(workspace_name, "GA", team2)
    
    # WHEN: Generating third team ID
    team_id_3 = generate_team_id(workspace_name, "GA")
    
    # THEN: Should get "3"
    assert team_id_3 == "3"


def test_add_team_with_assigned_clusters(temp_workspace):
    """Test adding a team with assigned_clusters field."""
    workspace_name, temp_dir = temp_workspace
    
    # GIVEN: A team with assigned clusters
    team = Team(
        team_id="1",
        team_name="ATL Team",
        city="Atlanta",
        assigned_clusters="C1-T1,C1-T2,C1-T3",
        contact_name="John Doe",
        contact_phone="555-1234",
        contact_email="john@example.com",
        created_date=date.today()
    )
    
    # WHEN: Adding the team
    result = add_team(workspace_name, "GA", team)
    
    # THEN: Team should be added successfully
    assert result.team_id == "1"
    assert result.assigned_clusters == "C1-T1,C1-T2,C1-T3"
    
    # AND: Team should be loadable
    teams = load_teams(workspace_name, "GA")
    assert len(teams) == 1
    assert teams[0].team_id == "1"
    assert teams[0].assigned_clusters == "C1-T1,C1-T2,C1-T3"


def test_add_team_without_assigned_clusters(temp_workspace):
    """Test adding a team without assigned_clusters (optional field)."""
    workspace_name, temp_dir = temp_workspace
    
    # GIVEN: A team without assigned clusters
    team = Team(
        team_id="1",
        team_name="Unassigned Team",
        city="Atlanta",
        assigned_clusters=None,
        created_date=date.today()
    )
    
    # WHEN: Adding the team
    result = add_team(workspace_name, "GA", team)
    
    # THEN: Team should be added successfully
    assert result.team_id == "1"
    assert result.assigned_clusters is None


def test_update_team_assigned_clusters(temp_workspace):
    """Test updating a team's assigned_clusters."""
    workspace_name, temp_dir = temp_workspace
    
    # GIVEN: An existing team with 3 cluster assignments
    team = Team(
        team_id="1",
        team_name="ATL Team",
        city="Atlanta",
        assigned_clusters="C1-T1,C1-T2,C1-T3",
        created_date=date.today()
    )
    add_team(workspace_name, "GA", team)
    
    # WHEN: Updating to only 2 cluster assignments
    updated_team = Team(
        team_id="1",
        team_name="ATL Team",
        city="Atlanta",
        assigned_clusters="C1-T1,C1-T2",  # Removed C1-T3
        created_date=date.today()
    )
    result = update_team(workspace_name, "GA", "1", updated_team)
    
    # THEN: Team should be updated
    assert result.assigned_clusters == "C1-T1,C1-T2"
    
    # AND: Changes should persist
    teams = load_teams(workspace_name, "GA")
    assert teams[0].assigned_clusters == "C1-T1,C1-T2"


def test_update_team_preserves_simple_id(temp_workspace):
    """Test that team_id remains simple even when updating other fields."""
    workspace_name, temp_dir = temp_workspace
    
    # GIVEN: A team with simple ID "1"
    team = Team(
        team_id="1",
        team_name="Original Name",
        city="Atlanta",
        assigned_clusters="C1-T1",
        created_date=date.today()
    )
    add_team(workspace_name, "GA", team)
    
    # WHEN: Updating team name and clusters
    updated_team = Team(
        team_id="1",
        team_name="Updated Name",
        city="Atlanta",
        assigned_clusters="C1-T1,C1-T2",
        created_date=date.today()
    )
    result = update_team(workspace_name, "GA", "1", updated_team)
    
    # THEN: team_id should remain "1"
    assert result.team_id == "1"
    assert result.team_name == "Updated Name"
    assert result.assigned_clusters == "C1-T1,C1-T2"


def test_delete_team_by_simple_id(temp_workspace):
    """Test deleting a team using simple ID."""
    workspace_name, temp_dir = temp_workspace
    
    # GIVEN: Multiple teams
    team1 = Team(team_id="1", team_name="Team 1", city="Atlanta", created_date=date.today())
    team2 = Team(team_id="2", team_name="Team 2", city="Atlanta", created_date=date.today())
    add_team(workspace_name, "GA", team1)
    add_team(workspace_name, "GA", team2)
    
    # WHEN: Deleting team "1"
    result = delete_team(workspace_name, "GA", "1")
    
    # THEN: Team should be deleted
    assert result is True
    
    # AND: Only team "2" should remain
    teams = load_teams(workspace_name, "GA")
    assert len(teams) == 1
    assert teams[0].team_id == "2"


def test_load_teams_returns_empty_list_when_no_file(temp_workspace):
    """Test that load_teams returns empty list when teams.csv doesn't exist."""
    workspace_name, temp_dir = temp_workspace
    
    # GIVEN: No teams.csv file exists
    # WHEN: Loading teams
    teams = load_teams(workspace_name, "GA")
    
    # THEN: Should return empty list
    assert teams == []


def test_multiple_teams_with_different_cluster_assignments(temp_workspace):
    """Test multiple teams with different cluster assignments."""
    workspace_name, temp_dir = temp_workspace
    
    # GIVEN: Multiple teams with different cluster assignments
    team1 = Team(
        team_id="1",
        team_name="North Team",
        city="Atlanta",
        assigned_clusters="C1-T1,C1-T2",
        created_date=date.today()
    )
    team2 = Team(
        team_id="2",
        team_name="South Team",
        city="Atlanta",
        assigned_clusters="C1-T3,C1-T4",
        created_date=date.today()
    )
    team3 = Team(
        team_id="3",
        team_name="Unassigned Team",
        city="Atlanta",
        assigned_clusters=None,
        created_date=date.today()
    )
    
    # WHEN: Adding all teams
    add_team(workspace_name, "GA", team1)
    add_team(workspace_name, "GA", team2)
    add_team(workspace_name, "GA", team3)
    
    # THEN: All teams should be loadable with correct assignments
    teams = load_teams(workspace_name, "GA")
    assert len(teams) == 3
    
    team_dict = {t.team_id: t for t in teams}
    assert team_dict["1"].assigned_clusters == "C1-T1,C1-T2"
    assert team_dict["2"].assigned_clusters == "C1-T3,C1-T4"
    assert team_dict["3"].assigned_clusters is None


def test_team_id_not_duplicated(temp_workspace):
    """Test that adding a team with duplicate ID raises error."""
    workspace_name, temp_dir = temp_workspace
    
    # GIVEN: A team with ID "1"
    team1 = Team(
        team_id="1",
        team_name="Team 1",
        city="Atlanta",
        created_date=date.today()
    )
    add_team(workspace_name, "GA", team1)
    
    # WHEN: Trying to add another team with same ID
    team2 = Team(
        team_id="1",
        team_name="Team 2",
        city="Atlanta",
        created_date=date.today()
    )
    
    # THEN: Should raise ValueError
    with pytest.raises(ValueError, match="already exists"):
        add_team(workspace_name, "GA", team2)


def test_update_nonexistent_team_raises_error(temp_workspace):
    """Test that updating a non-existent team raises error."""
    workspace_name, temp_dir = temp_workspace
    
    # GIVEN: No teams exist
    # WHEN: Trying to update team "999"
    team = Team(
        team_id="999",
        team_name="Ghost Team",
        city="Atlanta",
        created_date=date.today()
    )
    
    # THEN: Should raise ValueError
    with pytest.raises(ValueError, match="not found"):
        update_team(workspace_name, "GA", "999", team)


def test_delete_nonexistent_team_returns_false(temp_workspace):
    """Test that deleting a non-existent team returns False."""
    workspace_name, temp_dir = temp_workspace
    
    # GIVEN: No teams exist
    # WHEN: Trying to delete team "999"
    result = delete_team(workspace_name, "GA", "999")
    
    # THEN: Should return False
    assert result is False
