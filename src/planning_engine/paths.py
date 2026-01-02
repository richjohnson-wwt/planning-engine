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
    
    Sanitizes the workspace name to prevent path traversal attacks.
    
    Args:
        workspace_name: Name of the workspace
        
    Returns:
        Path to the workspace directory
        
    Raises:
        ValueError: If workspace name is empty or invalid
    """
    import re
    
    # Validate workspace name is not empty
    if not workspace_name or not workspace_name.strip():
        raise ValueError("Workspace name cannot be empty")
    
    # Remove any path separators and dangerous characters
    # Only allow alphanumeric, underscore, and hyphen (remove dots and slashes entirely)
    sanitized = re.sub(r'[^a-zA-Z0-9_\-]', '', workspace_name)
    
    # Remove leading/trailing underscores and hyphens
    sanitized = sanitized.strip('_-')
    
    # Validate the sanitized name is not empty
    if not sanitized:
        raise ValueError(
            f"Invalid workspace name: '{workspace_name}'. "
            "Workspace names must contain at least one alphanumeric character."
        )
    
    return get_project_root() / "data" / "workspace" / sanitized
