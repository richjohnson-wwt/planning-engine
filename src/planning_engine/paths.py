"""Path utilities for the planning engine.

This module provides utilities for resolving paths to the project root
and workspace directories, ensuring the library works correctly regardless
of where it's invoked from.
"""

from pathlib import Path
import os


def get_project_root() -> Path:
    """
    Get the project root directory (where data/ folder lives).
    
    Returns:
        Path to the project root directory
        
    Raises:
        RuntimeError: If project root cannot be found
    """
    # Start from this file's directory (inside src/planning_engine/)
    current = Path(__file__).resolve().parent
    
    # Search upward for the project root (max 10 levels)
    for _ in range(10):
        # Check if this directory contains 'src' folder and 'pyproject.toml'
        # These are more reliable markers than 'data' which might be created anywhere
        if (current / "src").exists() and (current / "pyproject.toml").exists():
            return current
        
        # Also check for pyproject.toml alone as a marker
        if (current / "pyproject.toml").exists():
            return current
        
        # Move up one level
        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent
    
    # If still not found, raise an error
    raise RuntimeError(
        "Could not find project root directory. "
        "Expected to find 'pyproject.toml' or 'src' directory in the project root. "
        f"Searched from {Path(__file__).resolve()} upward."
    )


def get_workspace_path(workspace_name: str) -> Path:
    """
    Get the path to a workspace directory.
    
    Args:
        workspace_name: Name of the workspace
        
    Returns:
        Path to the workspace directory
    """
    return get_project_root() / "data" / "workspace" / workspace_name
