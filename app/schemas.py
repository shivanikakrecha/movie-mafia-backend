from pydantic import BaseModel, EmailStr, Field, UUID4, HttpUrl, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID

# ---------- User Schemas ----------

class UserBase(BaseModel):
    email: EmailStr = Field(..., example="user@example.com")
    full_name: Optional[str] = Field(None, example="John Doe")
    is_active: Optional[bool] = Field(default=True)
    is_admin: Optional[bool] = Field(default=False)


class UserLogin(BaseModel):
    email: EmailStr = Field(..., example="user@example.com")
    password: str = Field(..., min_length=6, example="secret123")

    @validator("password")
    def validate_password(cls, value):
        if len(value) < 6:
            raise ValueError("Password must be at least 6 characters long.")
        return value


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, example="secret123")


class UserOut(UserBase):
    id: UUID4
    created_at: datetime
    last_login: Optional[datetime]

    class Config:
        orm_mode = True


# ---------- Movie Schemas ----------

class MovieBase(BaseModel):
    title: str = Field(..., min_length=1, example="Inception")
    year: int = Field(..., ge=1888, le=2100, example=2010)

    @validator("title")
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

    class Config:
        orm_mode = True


# ---------- Pagination Schema ----------

class PaginatedMovieOut(BaseModel):
    count: int = Field(..., example=42)
    totalPages: int = Field(..., example=6)
    data: List[MovieOut]

