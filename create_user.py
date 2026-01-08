#!/usr/bin/env python3
"""
Quick script to create a new user.
Run this while logged in as admin.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

# Add the apps/api directory to the path so we can import auth
sys.path.insert(0, str(Path(__file__).parent / "apps" / "api"))

from auth import create_user

def main():
    print("=== Create New User ===\n")
    
    username = input("Enter username: ").strip()
    if not username:
        print("Error: Username cannot be empty")
        return
    
    password = input("Enter password: ").strip()
    if not password:
        print("Error: Password cannot be empty")
        return
    
    is_admin_input = input("Make this user an admin? (y/N): ").strip().lower()
    is_admin = is_admin_input == 'y'
    
    try:
        user = create_user(username, password, is_admin)
        print(f"\n✓ User '{username}' created successfully!")
        print(f"  Admin: {user.is_admin}")
        print(f"  Created: {user.created_at}")
    except ValueError as e:
        print(f"\n✗ Error: {e}")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")

if __name__ == "__main__":
    main()
