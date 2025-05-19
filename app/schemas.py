from pydantic import UUID4, BaseModel, EmailStr
from uuid import UUID
from datetime import datetime
from typing import List, Optional

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    is_active: Optional[bool] = True
    is_admin: Optional[bool] = False

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserCreate(UserBase):
    password: str

class UserOut(UserBase):
    id: UUID
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        orm_mode = True

class MovieBase(BaseModel):
    title: str
    year: int

class MovieCreate(MovieBase):
    pass

# class MovieOut(MovieBase):
#     id: UUID
#     poster_url: Optional[str] = None
#     owner_id: UUID
#     created_at: datetime
#     updated_at: datetime

#     class Config:
#         orm_mode = True


class MovieOut(BaseModel):
    id: UUID4
    title: str
    poster_url: str
    year: int
    owner_id: UUID4
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class PaginatedMovieOut(BaseModel):
    count: int
    data: List[MovieOut]
    totalPages: int