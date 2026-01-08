from planning_engine import new_workspace
from pathlib import Path
import pytest
import shutil


def test_new_workspace_creates_directory():
    """Test that new_workspace creates the expected directory structure"""
    workspace_name = "test_workspace_123"
    
    try:
        # Create workspace
        workspace_path = new_workspace(workspace_name)
        
        # Verify workspace path exists
        assert workspace_path.exists()
        assert workspace_path.is_dir()
        assert workspace_path.name == workspace_name
        
        # Verify subdirectories exist
        assert (workspace_path / "input").exists()
        assert (workspace_path / "output").exists()
        assert (workspace_path / "cache").exists()
        
    finally:
        # Cleanup
        if Path("data/workspace").exists():
            shutil.rmtree("data/workspace/" + workspace_name, ignore_errors=True)


def test_new_workspace_sanitizes_name():
    """Test that workspace names are sanitized"""
    workspace_name = "test/../../../etc/passwd"
    
    try:
        workspace_path = new_workspace(workspace_name)
        
        # Should only contain safe characters - no path traversal
        assert ".." not in str(workspace_path)
        assert "/" not in workspace_path.name  # No slashes in the final directory name
        assert workspace_path.name == "testetcpasswd"
        # Verify it's under workspace directory (context-based path)
        assert "workspace" in str(workspace_path)
        
    finally:
        # Cleanup - handle both old and new path structures
        if Path("data/workspace/testetcpasswd").exists():
            shutil.rmtree("data/workspace/testetcpasswd", ignore_errors=True)
        if Path("workspace/testetcpasswd").exists():
            shutil.rmtree("workspace/testetcpasswd", ignore_errors=True)


def test_new_workspace_empty_name_raises_error():
    """Test that empty workspace names raise ValueError"""
    with pytest.raises(ValueError, match="Workspace name cannot be empty"):
        new_workspace("")
    
    with pytest.raises(ValueError, match="Workspace name cannot be empty"):
        new_workspace("   ")


def test_new_workspace_invalid_characters_raises_error():
    """Test that workspace names with only invalid characters raise ValueError"""
    with pytest.raises(ValueError, match="Invalid workspace name"):
        new_workspace("///")
    
    with pytest.raises(ValueError, match="Invalid workspace name"):
        new_workspace("...")


def test_new_workspace_idempotent():
    """Test that calling new_workspace multiple times with same name is safe"""
    workspace_name = "test_idempotent"
    
    try:
        # Create workspace twice
        path1 = new_workspace(workspace_name)
        path2 = new_workspace(workspace_name)
        
        # Should return same path
        assert path1 == path2
        assert path1.exists()
        
    finally:
        # Cleanup
        if Path("data/workspace").exists():
            shutil.rmtree("data/workspace/" + workspace_name, ignore_errors=True)
