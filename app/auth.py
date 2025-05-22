from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.config import get_settings
from app import models

settings = get_settings()

# OAuth2 scheme for token handling
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Error Messages
AUTH_ERRORS = {
    "CREDENTIALS_ERROR": "Could not validate credentials",
    "TOKEN_ERROR": "Invalid token",
    "USER_NOT_FOUND": "User not found",
    "INACTIVE_USER": "Inactive user",
}

class AuthError(HTTPException):
    """Custom exception for authentication errors"""
    def __init__(self, detail: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        super().__init__(
            status_code=status_code,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )

# ------------------------
# Password Hashing
# ------------------------
def get_password_hash(password: str) -> str:
    """Hash a plain-text password."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a hash."""
    return pwd_context.verify(plain_password, hashed_password)

# ------------------------
# JWT Token Creation
# ------------------------
def create_access_token(data: dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token.

    Args:
        data: The payload data (usually includes user ID or email)
        expires_delta: Optional timedelta to override default expiry

    Returns:
        JWT token as string
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY.get_secret_value(),
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

# ------------------------
# JWT Token Validation
# ------------------------
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> models.User:
    """
    Validate access token and return current user.

    Args:
        token: JWT token from request
        db: Database session

    Returns:
        User model instance

    Raises:
        AuthError: If token is invalid or user not found
    """
    try:
        # Decode token
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        if user_id is None:
            raise AuthError(AUTH_ERRORS["TOKEN_ERROR"])
        
        # Get user from database
        stmt = select(models.User).where(models.User.id == UUID(user_id))
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            raise AuthError(AUTH_ERRORS["USER_NOT_FOUND"])
        if not user.is_active:
            raise AuthError(AUTH_ERRORS["INACTIVE_USER"])
            
        return user
    except JWTError:
        raise AuthError(AUTH_ERRORS["CREDENTIALS_ERROR"])
    except ValueError:
        raise AuthError(AUTH_ERRORS["TOKEN_ERROR"])

async def get_current_active_user(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    """
    Get current user and verify they are active.

    Args:
        current_user: User model instance from get_current_user

    Returns:
        User model instance if active

    Raises:
        AuthError: If user is inactive
    """
    if not current_user.is_active:
        raise AuthError(
            AUTH_ERRORS["INACTIVE_USER"],
            status_code=status.HTTP_403_FORBIDDEN
        )
    return current_user

# ------------------------
# Token Decoding
# ------------------------
def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded token data

    Raises:
        ValueError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise ValueError(AUTH_ERRORS["TOKEN_ERROR"]) from e
