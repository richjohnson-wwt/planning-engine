"""
Simple authentication system for internal use.

Uses JWT tokens with long expiration (90 days) for convenience.
User data stored in simple JSON file.
"""
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import json

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import bcrypt
from pydantic import BaseModel


# Security configuration
SECRET_KEY = "planning-engine-secret-key-2025"  # TODO: Move to environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 90  # Long-lived token for internal use

# HTTP Bearer token scheme
security = HTTPBearer()


# Models
class User(BaseModel):
    username: str
    hashed_password: str
    is_admin: bool = False
    created_at: str


class UserInDB(User):
    pass


class Token(BaseModel):
    access_token: str
    token_type: str
    username: str


class LoginRequest(BaseModel):
    username: str
    password: str


class CreateUserRequest(BaseModel):
    username: str
    password: str
    is_admin: bool = False


class TokenData(BaseModel):
    username: Optional[str] = None


# User database file path
def get_users_file() -> Path:
    """Get path to users.json file."""
    # Store in project root data directory
    users_file = Path(__file__).parent.parent.parent / "data" / "users.json"
    users_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize with default admin user if file doesn't exist
    if not users_file.exists():
        default_users = {
            "admin": {
                "username": "admin",
                "hashed_password": get_password_hash("admin123"),
                "is_admin": True,
                "created_at": datetime.now().isoformat()
            }
        }
        with open(users_file, 'w') as f:
            json.dump(default_users, f, indent=2)
    
    return users_file


# Password utilities
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def get_password_hash(password: str) -> str:
    """Hash a password."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


# User database operations
def load_users() -> dict:
    """Load users from JSON file."""
    users_file = get_users_file()
    with open(users_file, 'r') as f:
        return json.load(f)


def save_users(users: dict):
    """Save users to JSON file."""
    users_file = get_users_file()
    with open(users_file, 'w') as f:
        json.dump(users, f, indent=2)


def get_user(username: str) -> Optional[UserInDB]:
    """Get user by username."""
    users = load_users()
    if username in users:
        return UserInDB(**users[username])
    return None


def create_user(username: str, password: str, is_admin: bool = False) -> UserInDB:
    """Create a new user."""
    users = load_users()
    
    if username in users:
        raise ValueError(f"User '{username}' already exists")
    
    user_data = {
        "username": username,
        "hashed_password": get_password_hash(password),
        "is_admin": is_admin,
        "created_at": datetime.now().isoformat()
    }
    
    users[username] = user_data
    save_users(users)
    
    return UserInDB(**user_data)


def delete_user(username: str) -> bool:
    """Delete a user."""
    users = load_users()
    
    if username not in users:
        return False
    
    # Prevent deleting the last admin
    if users[username].get("is_admin"):
        admin_count = sum(1 for u in users.values() if u.get("is_admin"))
        if admin_count <= 1:
            raise ValueError("Cannot delete the last admin user")
    
    del users[username]
    save_users(users)
    return True


def list_users() -> list[User]:
    """List all users (without passwords)."""
    users = load_users()
    return [User(**user_data) for user_data in users.values()]


# Authentication
def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """Authenticate a user with username and password."""
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserInDB:
    """Get the current authenticated user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    
    return user


from fastapi import Request
from fastapi.security import HTTPBearer as HTTPBearerBase
from typing import Optional as OptionalType

# Create an optional HTTPBearer that doesn't fail if no credentials are provided
class OptionalHTTPBearer(HTTPBearerBase):
    async def __call__(self, request: Request) -> OptionalType[HTTPAuthorizationCredentials]:
        try:
            return await super().__call__(request)
        except HTTPException:
            return None

optional_security = OptionalHTTPBearer()


async def get_current_user_optional_token(
    token: str = None,
    credentials: OptionalType[HTTPAuthorizationCredentials] = Depends(optional_security)
) -> UserInDB:
    """Get the current authenticated user from JWT token (supports both header and query param)."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Try to get token from Authorization header first, then from query parameter
    jwt_token = None
    
    if credentials:
        jwt_token = credentials.credentials
    elif token:
        jwt_token = token
    
    if not jwt_token:
        raise credentials_exception
    
    try:
        payload = jwt.decode(jwt_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    user = get_user(username=token_data.username)
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_admin_user(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
    """Get the current user and verify they are an admin."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


# Optional dependency - returns None if not authenticated
async def get_current_user_optional(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[UserInDB]:
    """Get current user if authenticated, None otherwise."""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
