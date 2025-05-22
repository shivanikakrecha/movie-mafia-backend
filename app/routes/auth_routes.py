from datetime import datetime
from typing import Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from app.database import get_db
from app import schemas, models, auth

# Constants
MAX_LOGIN_ATTEMPTS = 5
LOGIN_ATTEMPT_WINDOW = 15 * 60  # 15 minutes in seconds

# Error Messages
ERROR_MESSAGES = {
    "EMAIL_EXISTS": "Email already registered",
    "INVALID_CREDENTIALS": "Invalid email or password",
    "DB_ERROR": "Database operation failed",
    "TOO_MANY_ATTEMPTS": "Too many login attempts. Please try again later",
    "USER_NOT_FOUND": "User not found",
    "USER_INACTIVE": "User account is inactive",
    "REGISTRATION_FAILED": "Failed to register user",
}

class AuthException(HTTPException):
    """Custom exception for authentication-related errors with logging capability"""
    def __init__(self, status_code: int, detail: str, log_error: bool = True):
        super().__init__(status_code=status_code, detail=detail)
        if log_error:
            # In a production environment, you would want to use proper logging
            print(f"AuthException: {status_code} - {detail}")

class AuthOperations:
    """Handle authentication operations with proper error handling"""
    
    @staticmethod
    async def get_user_by_email(email: str, db: AsyncSession) -> models.User:
        """Get user by email with proper error handling"""
        try:
            stmt = select(models.User).where(
                and_(
                    models.User.email == email,
                    models.User.is_active == True
                )
            )
            result = await db.execute(stmt)
            user = result.scalar_one_or_none()
            if user is None:
                print(f"No user found with email: {email}")
            return user
        except SQLAlchemyError as e:
            print(f"Database error in get_user_by_email: {str(e)}")
            await db.rollback()
            raise AuthException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database error: {str(e)}"
            )
        except Exception as e:
            print(f"Unexpected error in get_user_by_email: {str(e)}")
            await db.rollback()
            raise AuthException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ERROR_MESSAGES["DB_ERROR"]
            )

    @staticmethod
    async def create_user(user_data: schemas.UserCreate, db: AsyncSession) -> models.User:
        """Create a new user with proper error handling"""
        try:
            hashed_password = auth.get_password_hash(user_data.password)
            now = datetime.utcnow()
            
            new_user = models.User(
                email=user_data.email,
                full_name=user_data.full_name,
                hashed_password=hashed_password,
                created_at=now,
                last_login=now
            )
            
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)
            return new_user
        except IntegrityError:
            await db.rollback()
            raise AuthException(
                status_code=status.HTTP_409_CONFLICT,
                detail=ERROR_MESSAGES["EMAIL_EXISTS"]
            )
        except SQLAlchemyError as e:
            await db.rollback()
            raise AuthException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=ERROR_MESSAGES["REGISTRATION_FAILED"]
            )

    @staticmethod
    async def update_last_login(user: models.User, db: AsyncSession) -> None:
        """Update user's last login timestamp"""
        try:
            user.last_login = datetime.utcnow()
            await db.commit()
        except SQLAlchemyError:
            await db.rollback()
            # Don't raise an exception here as this is not critical for login

    @staticmethod
    def create_token_response(user_id: UUID) -> Dict[str, str]:
        """Create standardized token response"""
        token = auth.create_access_token({"sub": str(user_id)})
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }

class InputValidator:
    """Handle input validation"""
    
    @staticmethod
    def validate_email(email: str) -> None:
        """Additional email validation if needed"""
        # Add any additional email validation logic here
        pass

    @staticmethod
    def validate_password(password: str) -> None:
        """Additional password validation if needed"""
        # Add any additional password validation logic here
        pass

router = APIRouter(
    tags=["Authentication"]
)

@router.post(
    "/register",
    response_model=schemas.UserResponse,
    status_code=status.HTTP_201_CREATED
)
async def register(
    user: schemas.UserCreate,
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Register a new user
    
    Args:
        user: User registration data
        db: Database session
    
    Returns:
        Dict containing success message and user data
    
    Raises:
        AuthException: If registration fails
    """
    try:
        # Validate input
        InputValidator.validate_email(user.email)
        InputValidator.validate_password(user.password)
        
        # Check if user exists
        existing_user = await AuthOperations.get_user_by_email(user.email, db)
        if existing_user:
            raise AuthException(
                status_code=status.HTTP_409_CONFLICT,
                detail=ERROR_MESSAGES["EMAIL_EXISTS"]
            )
        
        # Create new user
        new_user = await AuthOperations.create_user(user, db)
        
        return {
            "status": "success",
            "message": "Registration successful",
            "user": {
                "id": new_user.id,
                "email": new_user.email,
                "full_name": new_user.full_name,
                "is_active": new_user.is_active,
                "created_at": new_user.created_at
            }
        }
    except Exception as e:
        if isinstance(e, AuthException):
            raise
        raise AuthException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/login", response_model=schemas.TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    Authenticate user and return access token
    
    Args:
        form_data: Login credentials
        db: Database session
    
    Returns:
        Dict containing access token and token type
    
    Raises:
        AuthException: If authentication fails
    """
    try:
        # Get user from database
        user = await AuthOperations.get_user_by_email(form_data.username, db)
        
        # Validate user exists and is active
        if not user:
            raise AuthException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES["INVALID_CREDENTIALS"]
            )
        
        if not user.is_active:
            raise AuthException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES["USER_INACTIVE"]
            )
        
        # Verify password
        if not auth.verify_password(form_data.password, user.hashed_password):
            raise AuthException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=ERROR_MESSAGES["INVALID_CREDENTIALS"]
            )
        
        # Update last login timestamp
        await AuthOperations.update_last_login(user, db)
        
        # Generate and return token
        return AuthOperations.create_token_response(user.id)
    except Exception as e:
        if isinstance(e, AuthException):
            raise
        raise AuthException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/refresh", response_model=schemas.TokenResponse)
async def refresh_token(
    current_user: UUID = Depends(auth.get_current_user)
) -> Dict[str, str]:
    """
    Refresh access token
    
    Args:
        current_user: Current authenticated user ID
    
    Returns:
        Dict containing new access token and token type
    """
    return AuthOperations.create_token_response(current_user)
