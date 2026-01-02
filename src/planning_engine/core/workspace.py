"""Workspace management and validation utilities."""

from pathlib import Path
from ..paths import get_workspace_path as _get_workspace_path


def get_workspace_path(workspace_name: str) -> Path:
    """
    Get the path to a workspace directory.
    
    Args:
        workspace_name: Name of the workspace
        
    Returns:
        Path to the workspace directory
    """
    return _get_workspace_path(workspace_name)


def validate_workspace(workspace_name: str) -> Path:
    """
    Validate that a workspace exists.
    
    Args:
        workspace_name: Name of the workspace
        
    Returns:
        Path to the workspace directory
        
    Raises:
        FileNotFoundError: If workspace doesn't exist
    """
    workspace_path = get_workspace_path(workspace_name)
    if not workspace_path.exists():
        raise FileNotFoundError(
            f"Workspace '{workspace_name}' does not exist. "
            f"Create it first using new_workspace('{workspace_name}')"
        )
    return workspace_path


def validate_state_file(
    workspace_path: Path,
    state_abbr: str,
    filename: str,
    file_type: str = "file"
) -> Path:
    """
    Validate that a state-specific file exists in the workspace.
    
    Args:
        workspace_path: Path to workspace directory
        state_abbr: State abbreviation (e.g., "LA", "NC")
        filename: Name of the file to check (e.g., "geocoded.csv")
        file_type: Description of file type for error messages
        
    Returns:
        Path to the validated file
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    # Determine directory based on filename
    if filename in ["addresses.csv"]:
        file_path = workspace_path / "input" / state_abbr / filename
    else:
        file_path = workspace_path / "cache" / state_abbr / filename
    
    if not file_path.exists():
        raise FileNotFoundError(
            f"{file_type} not found for state '{state_abbr}'. "
            f"Expected path: {file_path}"
        )
    
    return file_path
