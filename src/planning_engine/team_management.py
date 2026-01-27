"""Team management functionality for tracking crews/teams per state.

Teams are stored in state-specific CSV files at:
data/workspace/{workspace_name}/cache/{state}/teams.csv

This module provides CRUD operations for team management.
"""

from pathlib import Path
from typing import List, Optional
import pandas as pd
from datetime import date, datetime

from .models import Team, TeamListResponse
from .core.workspace import validate_workspace, validate_state_file


def get_teams_csv_path(workspace_name: str, state_abbr: str) -> Path:
    """Get the path to the teams.csv file for a workspace and state.
    
    Args:
        workspace_name: Name of the workspace
        state_abbr: State name or abbreviation (e.g., "Kansas", "KS", "LA", "NC")
                   Uses whatever format is in the directory structure
        
    Returns:
        Path to teams.csv file
    """
    workspace_path = validate_workspace(workspace_name)
    # Use the state name as-is (could be full name like "Kansas" or abbreviation like "KS")
    teams_csv = workspace_path / "cache" / state_abbr / "teams.csv"
    
    # Ensure the state cache directory exists
    teams_csv.parent.mkdir(parents=True, exist_ok=True)
    
    return teams_csv


def load_teams(workspace_name: str, state_abbr: str) -> List[Team]:
    """Load all teams for a workspace and state.
    
    Args:
        workspace_name: Name of the workspace
        state_abbr: State abbreviation
        
    Returns:
        List of Team objects
    """
    import logging
    from .paths import get_current_username
    
    logger = logging.getLogger(__name__)
    
    teams_csv = get_teams_csv_path(workspace_name, state_abbr)
    
    current_username = get_current_username()
    logger.info(f"load_teams: workspace={workspace_name}, state={state_abbr}, username_context={current_username}")
    logger.info(f"load_teams: teams_csv={teams_csv}, exists={teams_csv.exists()}")
    
    if not teams_csv.exists():
        logger.info(f"load_teams: teams.csv does not exist, returning empty list")
        return []
    
    try:
        df = pd.read_csv(teams_csv)
        
        if df.empty:
            return []
        
        # Convert DataFrame to list of Team objects
        teams = []
        for _, row in df.iterrows():
            team_data = row.to_dict()
            
            # Convert team_id to string (pandas may read it as int)
            if 'team_id' in team_data:
                team_data['team_id'] = str(team_data['team_id'])
            
            # Handle date fields
            for date_field in ['availability_start', 'availability_end', 'created_date']:
                if date_field in team_data and pd.notna(team_data[date_field]):
                    try:
                        team_data[date_field] = pd.to_datetime(team_data[date_field]).date()
                    except:
                        team_data[date_field] = None
                else:
                    team_data[date_field] = None
            
            # Handle assigned_clusters (can be null)
            if 'assigned_clusters' in team_data and pd.notna(team_data['assigned_clusters']):
                team_data['assigned_clusters'] = str(team_data['assigned_clusters'])
            else:
                team_data['assigned_clusters'] = None
            
            # Handle optional string fields - convert to string if present, None if missing
            for field in ['contact_name', 'contact_phone', 'contact_email']:
                if field in team_data:
                    if pd.isna(team_data[field]):
                        team_data[field] = None
                    else:
                        # Convert to string (handles case where pandas reads phone as int)
                        team_data[field] = str(team_data[field])
            
            # Handle notes field - always a string, never None
            if 'notes' in team_data:
                if pd.isna(team_data['notes']):
                    team_data['notes'] = ""
                else:
                    team_data['notes'] = str(team_data['notes'])
            
            teams.append(Team(**team_data))
        
        logger.info(f"load_teams: successfully loaded {len(teams)} teams")
        return teams
    
    except Exception as e:
        logger.error(f"load_teams: Failed to load teams from {teams_csv}: {str(e)}", exc_info=True)
        raise ValueError(f"Failed to load teams from {teams_csv}: {str(e)}")


def save_teams(workspace_name: str, state_abbr: str, teams: List[Team]) -> Path:
    """Save teams to CSV file, overwriting existing file.
    
    Args:
        workspace_name: Name of the workspace
        state_abbr: State abbreviation
        teams: List of Team objects to save
        
    Returns:
        Path to the saved teams.csv file
    """
    import logging
    from .paths import get_current_username
    
    logger = logging.getLogger(__name__)
    
    teams_csv = get_teams_csv_path(workspace_name, state_abbr)
    current_username = get_current_username()
    
    logger.info(f"save_teams: workspace={workspace_name}, state={state_abbr}, num_teams={len(teams)}, username_context={current_username}")
    logger.info(f"save_teams: saving to {teams_csv}")
    
    if not teams:
        # If no teams, create empty file with headers
        df = pd.DataFrame(columns=[
            'team_id', 'team_name', 'city', 'cluster_id',
            'contact_name', 'contact_phone', 'contact_email',
            'availability_start', 'availability_end', 'notes', 'created_date'
        ])
    else:
        # Convert teams to DataFrame
        team_dicts = [team.model_dump() for team in teams]
        df = pd.DataFrame(team_dicts)
    
    # Save to CSV
    df.to_csv(teams_csv, index=False)
    logger.info(f"save_teams: successfully saved {len(teams)} teams to {teams_csv}")
    
    return teams_csv


def add_team(workspace_name: str, state_abbr: str, team: Team) -> Team:
    """Add a new team to the workspace/state.
    
    Args:
        workspace_name: Name of the workspace
        state_abbr: State abbreviation
        team: Team object to add
        
    Returns:
        The added Team object
        
    Raises:
        ValueError: If team_id already exists
    """
    import logging
    from .paths import get_current_username
    
    logger = logging.getLogger(__name__)
    
    current_username = get_current_username()
    logger.info(f"add_team: workspace={workspace_name}, state={state_abbr}, team_id={team.team_id}, username_context={current_username}")
    
    teams = load_teams(workspace_name, state_abbr)
    logger.info(f"add_team: loaded {len(teams)} existing teams")
    
    # Check for duplicate team_id
    if any(t.team_id == team.team_id for t in teams):
        logger.error(f"add_team: duplicate team_id={team.team_id}")
        raise ValueError(f"Team with ID '{team.team_id}' already exists")
    
    # Set created_date if not provided
    if team.created_date is None:
        team.created_date = date.today()
    
    teams.append(team)
    logger.info(f"add_team: appended team, now have {len(teams)} teams")
    
    saved_path = save_teams(workspace_name, state_abbr, teams)
    logger.info(f"add_team: saved teams to {saved_path}")
    
    return team


def update_team(workspace_name: str, state_abbr: str, team_id: str, updated_team: Team) -> Team:
    """Update an existing team.
    
    Args:
        workspace_name: Name of the workspace
        state_abbr: State abbreviation
        team_id: ID of the team to update
        updated_team: Updated Team object
        
    Returns:
        The updated Team object
        
    Raises:
        ValueError: If team_id not found
    """
    teams = load_teams(workspace_name, state_abbr)
    
    # Find and update the team
    found = False
    for i, team in enumerate(teams):
        if team.team_id == team_id:
            teams[i] = updated_team
            found = True
            break
    
    if not found:
        raise ValueError(f"Team with ID '{team_id}' not found")
    
    save_teams(workspace_name, state_abbr, teams)
    
    return updated_team


def delete_team(workspace_name: str, state_abbr: str, team_id: str) -> bool:
    """Delete a team.
    
    Args:
        workspace_name: Name of the workspace
        state_abbr: State abbreviation
        team_id: ID of the team to delete
        
    Returns:
        True if team was deleted, False if not found
    """
    teams = load_teams(workspace_name, state_abbr)
    
    # Filter out the team to delete
    original_count = len(teams)
    teams = [t for t in teams if t.team_id != team_id]
    
    if len(teams) == original_count:
        return False
    
    save_teams(workspace_name, state_abbr, teams)
    
    return True


def generate_team_id(workspace_name: str, state_abbr: str) -> str:
    """Generate a unique team ID for a state.
    
    Format: Simple sequential number (1, 2, 3, etc.)
    
    Args:
        workspace_name: Name of the workspace
        state_abbr: State abbreviation
        
    Returns:
        Generated team ID as a string
    """
    teams = load_teams(workspace_name, state_abbr)
    
    # Find the highest numeric ID used
    max_num = 0
    
    for team in teams:
        try:
            num = int(team.team_id)
            max_num = max(max_num, num)
        except ValueError:
            # Skip non-numeric IDs
            continue
    
    # Generate next ID
    next_num = max_num + 1
    return str(next_num)


def get_available_cities(workspace_name: str, state_abbr: str) -> List[str]:
    """Get list of cities from geocoded sites in a state.
    
    Useful for populating city dropdown in UI.
    
    Args:
        workspace_name: Name of the workspace
        state_abbr: State abbreviation
        
    Returns:
        Sorted list of unique city names
    """
    workspace_path = validate_workspace(workspace_name)
    geocoded_csv = workspace_path / "cache" / state_abbr / "geocoded.csv"
    
    if not geocoded_csv.exists():
        return []
    
    try:
        df = pd.read_csv(geocoded_csv)
        
        if 'city' not in df.columns:
            return []
        
        cities = df['city'].dropna().unique().tolist()
        return sorted(cities)
    
    except Exception as e:
        print(f"Warning: Could not load cities from geocoded.csv: {e}")
        return []
