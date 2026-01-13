"""
Authentication and User Management API Router
"""
from fastapi import APIRouter, Depends, HTTPException
from datetime import timedelta

# Import authentication utilities
# Try relative import first (for production/module mode), fall back to absolute (for dev)
try:
    from ..auth import (
        authenticate_user, create_access_token, get_current_user,
        get_current_admin_user, create_user, delete_user, list_users,
        User, UserInDB, Token, LoginRequest, CreateUserRequest,
        ACCESS_TOKEN_EXPIRE_DAYS
    )
except ImportError:
    from auth import (
        authenticate_user, create_access_token, get_current_user,
        get_current_admin_user, create_user, delete_user, list_users,
        User, UserInDB, Token, LoginRequest, CreateUserRequest,
        ACCESS_TOKEN_EXPIRE_DAYS
    )

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=Token)
def login(login_request: LoginRequest):
    """
    Login endpoint - returns JWT token with long expiration (90 days).
    
    Default admin credentials:
    - username: admin
    - password: admin123
    """
    user = authenticate_user(login_request.username, login_request.password)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )
    
    # Create access token with long expiration
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        username=user.username
    )


@router.post("/logout")
def logout(current_user: UserInDB = Depends(get_current_user)):
    """
    Logout endpoint - client should discard the token.
    Server doesn't track tokens, so this is just for client-side cleanup.
    """
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=User)
def get_current_user_info(current_user: UserInDB = Depends(get_current_user)):
    """Get current authenticated user information."""
    return current_user


@router.get("/users", response_model=list[User])
def get_users(current_user: UserInDB = Depends(get_current_admin_user)):
    """List all users (admin only)."""
    return list_users()


@router.post("/users", response_model=User)
def create_new_user(
    user_request: CreateUserRequest,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Create a new user (admin only)."""
    try:
        user = create_user(
            username=user_request.username,
            password=user_request.password,
            is_admin=user_request.is_admin
        )
        return user
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/users/{username}")
def delete_user_endpoint(
    username: str,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Delete a user (admin only)."""
    if username == current_user.username:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    try:
        success = delete_user(username)
        if not success:
            raise HTTPException(status_code=404, detail="User not found")
        return {"message": f"User '{username}' deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
