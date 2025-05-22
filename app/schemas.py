import re
from pydantic import BaseModel, EmailStr, Field, UUID4, HttpUrl, field_validator, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID

# ---------- User Schemas ----------

class UserBase(BaseModel):
    email: EmailStr = Field(..., example="user@example.com")
    full_name: str = Field(..., example="John Doe")
    is_active: Optional[bool] = Field(default=True)
    is_admin: Optional[bool] = Field(default=False)

    @field_validator('full_name')
    def validate_full_name(cls, v):
        if len(v.strip()) < 3:
            raise ValueError("Full name must be at least 3 characters long")
        if len(v.split()) < 2:
            raise ValueError("Please enter your full name (first and last name)")
        if not all(part.isalpha() for part in v.replace("  ", " ").split()):
            raise ValueError("Full name must contain only alphabetic characters")
        return v
    
    @field_validator('email')
    def validate_email(cls, v):
        email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(email_regex, v):
            raise ValueError("Please enter a valid email address")
        return v

class UserLogin(BaseModel):
    email: EmailStr = Field(..., example="user@example.com")
    password: str = Field(..., min_length=6, example="Secret@123")

    @field_validator('email')
    def validate_email(cls, v):
        email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(email_regex, v):
            raise ValueError("Please enter a valid email address")
        return v

    @field_validator('password')
    def validate_password_complexity(cls, v):
        if (len(v) < 8 or
            not re.search(r'[A-Z]', v) or
            not re.search(r'[a-z]', v) or
            not re.search(r'\d', v) or
            not re.search(r'[!@#$%^&*(),.?":{}|<>]', v)):
            raise ValueError("Password must be at least 8 characters long and include a capital letter, lowercase letter, number, and special character")
        return v

class UserCreate(UserBase):
    password: str = Field(..., min_length=6, example="Secret@123")

    @field_validator('password')
    def validate_password_complexity(cls, v):
        if (len(v) < 8 or
            not re.search(r'[A-Z]', v) or
            not re.search(r'[a-z]', v) or
            not re.search(r'\d', v) or
            not re.search(r'[!@#$%^&*(),.?":{}|<>]', v)):
            raise ValueError("Password must be at least 8 characters long and include a capital letter, lowercase letter, number, and special character")
        return v

class UserOut(UserBase):
    id: UUID4
    created_at: datetime
    last_login: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)

class UserResponse(BaseModel):
    """Response model for user operations"""
    status: str = Field(..., example="success")
    message: str = Field(..., example="Operation successful")
    user: Optional[Dict[str, Any]] = Field(None, example={
        "id": "123e4567-e89b-12d3-a456-426614174000",
        "email": "user@example.com",
        "full_name": "John Doe",
        "is_active": True,
        "created_at": "2024-01-01T00:00:00Z"
    })

    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    """Response model for token operations"""
    access_token: str = Field(..., example="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...")
    token_type: str = Field(..., example="bearer")
    expires_in: int = Field(..., example=1800)  # 30 minutes in seconds

    model_config = ConfigDict(from_attributes=True)

# ---------- Movie Schemas ----------

class MovieBase(BaseModel):
    title: str = Field(..., min_length=1, example="Inception")
    year: int = Field(..., ge=1888, le=2100, example=2010)

    @field_validator("title")
    def validate_title(cls, value):
        if not value.strip():
            raise ValueError("Movie title cannot be empty or just spaces.")
        return value


class MovieCreate(MovieBase):
    poster_url: HttpUrl = Field(..., example="https://example.com/poster.jpg")


class MovieUpdate(BaseModel):
    title: Optional[str] = Field(None, example="Updated Title")
    year: Optional[int] = Field(None, ge=1888, le=2100, example=2022)
    poster_url: Optional[HttpUrl] = Field(None, example="https://example.com/new-poster.jpg")


class MovieOut(MovieBase):
    id: UUID4
    poster_url: HttpUrl
    owner_id: UUID4
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------- Pagination Schema ----------

class PaginatedMovieOut(BaseModel):
    count: int = Field(..., example=42)
    totalPages: int = Field(..., example=6)
    data: List[MovieOut]

    model_config = ConfigDict(from_attributes=True)

