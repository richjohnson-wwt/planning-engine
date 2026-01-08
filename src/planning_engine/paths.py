"""Path utilities for the planning engine.

This module provides utilities for resolving paths to the project root
and workspace directories, ensuring the library works correctly regardless
of where it's invoked from.

For authenticated API requests, the workspace root can be scoped to a specific user
by setting the _current_username context variable.
"""

from pathlib import Path
import os
from contextvars import ContextVar

# Context variable to store current authenticated username
# When set, workspace paths become: data/{username}/workspace/{workspace_name}
# When not set, workspace paths remain: data/workspace/{workspace_name}
_current_username: ContextVar[str] = ContextVar('current_username', default=None)


def set_current_username(username: str):
    """Set the current username context for user-scoped workspace paths."""
    _current_username.set(username)


def get_current_username() -> str:
    """Get the current username context, or None if not set."""
    return _current_username.get()


def clear_current_username():
    """Clear the current username context."""
    _current_username.set(None)


def get_project_root() -> Path:
    """
    Get the project root directory (where data/ folder lives).
    
    If a username context is set (via set_current_username), returns data/{username}/
    Otherwise returns the standard project root.
    
    Returns:
        Path to the project root directory (or user-scoped root if username is set)
        
    Raises:
        RuntimeError: If project root cannot be found
    """
    # Start from this file's directory (inside src/planning_engine/)
    current = Path(__file__).resolve().parent
    
    # Search upward for the project root (max 10 levels)
    project_root = None
    for _ in range(10):
        # Check if this directory contains 'src' folder and 'pyproject.toml'
        # These are more reliable markers than 'data' which might be created anywhere
        if (current / "src").exists() and (current / "pyproject.toml").exists():
            project_root = current
            break
        
        # Also check for pyproject.toml alone as a marker
        if (current / "pyproject.toml").exists():
            project_root = current
            break
        
        # Move up one level
        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent
    
    # If still not found, raise an error
    if project_root is None:
        raise RuntimeError(
            "Could not find project root directory. "
            "Expected to find 'pyproject.toml' or 'src' directory in the project root. "
            f"Searched from {Path(__file__).resolve()} upward."
        )
    
    # If username context is set, return user-scoped root: data/{username}
    username = get_current_username()
    if username:
        return project_root / "data" / username
    
    # Otherwise return standard project root
    return project_root


def get_workspace_path(workspace_name: str) -> Path:
    """
    Get the path to a workspace directory.
    
    Sanitizes the workspace name to prevent path traversal attacks.
    Uses context-based user scoping when username is set via set_current_username().
    
    When username context is set: {project_root}/data/{username}/workspace/{workspace_name}
    When no username context: {project_root}/data/workspace/{workspace_name}
    
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
    
    # Check if username context is set
    username = get_current_username()
    
    if username:
        # User-scoped path: {project_root}/data/{username}/workspace/{workspace_name}
        # get_project_root() already returns {project_root}/data/{username}
        root = get_project_root()
        return root / "workspace" / sanitized
    else:
        # No username context: use standard path {project_root}/data/workspace/{workspace_name}
        # get_project_root() returns just {project_root}
        root = get_project_root()
        return root / "data" / "workspace" / sanitized
