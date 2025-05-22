import csv
from datetime import datetime
import io
import math
import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import (
    APIRouter, Depends, File, Form, UploadFile,
    HTTPException, status, BackgroundTasks, Request
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from jose import jwt, JWTError

from app.database import get_db
from app import models, schemas
from app.auth import SECRET_KEY, ALGORITHM
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Constants
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
CHUNK_SIZE = 1024 * 1024  # 1 MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png"}
POSTER_DIR = Path("static/posters")
MAX_TITLE_LENGTH = 100
MIN_YEAR = 1888
DEFAULT_PAGE_SIZE = 8
MAX_PAGE_SIZE = 100

class MovieException(HTTPException):
    """Custom exception for movie-related errors"""
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UUID:
    """Validate JWT token and return user ID"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = UUID(payload.get("sub"))
        if not user_id:
            raise MovieException(status_code=401, detail="Invalid token payload")
        return user_id
    except (JWTError, ValueError) as e:
        raise MovieException(status_code=401, detail="Could not validate credentials")

def get_full_url(request: Request, path: str) -> str:
    """Convert relative path to full URL"""
    base_url = str(request.base_url).rstrip('/')
    path = str(path).lstrip('/')
    return f"{base_url}/{path}"

async def save_poster_file(poster: UploadFile, background_tasks: BackgroundTasks) -> str:
    """Save poster file with validation and cleanup"""
    if not poster.filename:
        raise MovieException(status_code=400, detail="No filename provided")
    
    if poster.content_type not in ALLOWED_IMAGE_TYPES:
        raise MovieException(
            status_code=400, 
            detail=f"Unsupported file type. Allowed types: {', '.join(ALLOWED_IMAGE_TYPES)}"
        )

    try:
        POSTER_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().timestamp()
        safe_filename = f"{timestamp}_{poster.filename.replace(' ', '_')}"
        file_path = POSTER_DIR / safe_filename
        
        total_size = 0
        with file_path.open("wb") as buffer:
            while chunk := await poster.read(CHUNK_SIZE):
                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE:
                    background_tasks.add_task(file_path.unlink)
                    raise MovieException(
                        status_code=413,
                        detail=f"File size exceeds {MAX_FILE_SIZE // (1024 * 1024)} MB limit"
                    )
                buffer.write(chunk)
        
        return str(file_path)
    except Exception as e:
        if file_path.exists():
            background_tasks.add_task(file_path.unlink)
        raise MovieException(status_code=500, detail=f"Failed to save file: {str(e)}")
    finally:
        await poster.close()

async def validate_movie_input(title: str, year: int) -> None:
    """Validate movie input parameters"""
    if not title or len(title.strip()) < 1:
        raise MovieException(status_code=400, detail="Title cannot be empty")
    
    if len(title.strip()) > MAX_TITLE_LENGTH:
        raise MovieException(status_code=400, detail=f"Title must not exceed {MAX_TITLE_LENGTH} characters")
    
    current_year = datetime.now().year
    if year < MIN_YEAR or year > current_year:
        raise MovieException(status_code=400, detail=f"Year must be between {MIN_YEAR} and {current_year}")

async def get_movie_by_id_and_owner(movie_id: UUID, user_id: UUID, db: AsyncSession) -> models.Movie:
    """Get movie by ID and verify ownership"""
    try:
        result = await db.execute(
            select(models.Movie).where(
                models.Movie.id == movie_id,
                models.Movie.owner_id == user_id
            )
        )
        movie = result.scalar_one_or_none()
        if not movie:
            raise MovieException(status_code=404, detail="Movie not found")
        return movie
    except SQLAlchemyError as e:
        raise MovieException(status_code=500, detail="Database error occurred")

def transform_movie_response(movie: models.Movie, request: Request) -> Dict[str, Any]:
    """Transform movie model to response format"""
    return {
        "id": movie.id,
        "title": movie.title,
        "year": movie.year,
        "poster_url": get_full_url(request, movie.poster_url),
        "owner_id": movie.owner_id,
        "created_at": movie.created_at or datetime.utcnow(),
        "updated_at": movie.updated_at or datetime.utcnow()
    }

router = APIRouter(
    prefix="/movies",
    tags=["Movies"],
    dependencies=[Depends(get_current_user)]
)

@router.post("/", response_model=schemas.MovieOut, status_code=status.HTTP_201_CREATED)
async def create_movie(
    request: Request,
    background_tasks: BackgroundTasks,
    title: str = Form(...),
    year: int = Form(...),
    poster: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """Create a new movie entry"""
    try:
        await validate_movie_input(title, year)
        poster_path = await save_poster_file(poster, background_tasks)
        
        now = datetime.utcnow()
        new_movie = models.Movie(
            title=title.strip(),
            year=year,
            poster_url=get_full_url(request, poster_path),
            owner_id=user_id,
            created_at=now,
            updated_at=now
        )
        
        db.add(new_movie)
        await db.commit()
        await db.refresh(new_movie)
        return new_movie
    except SQLAlchemyError as e:
        await db.rollback()
        if poster_path:
            background_tasks.add_task(Path(poster_path).unlink)
        raise MovieException(status_code=500, detail="Failed to create movie")

@router.post("/bulk-upload/", status_code=status.HTTP_201_CREATED)
async def bulk_upload_movies(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """Bulk upload movies from CSV file"""
    if not file.filename.endswith('.csv'):
        raise MovieException(status_code=400, detail="Only CSV files are allowed")

    try:
        contents = await file.read()
        decoded = contents.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(decoded))
        required_fields = {'title', 'year', 'poster_url'}
        
        if not set(csv_reader.fieldnames or []).issuperset(required_fields):
            raise MovieException(
                status_code=400, 
                detail=f"CSV must contain fields: {', '.join(required_fields)}"
            )

        created_count = 0
        skipped_rows = []
        movies_to_add = []

        async with db.begin():
            for index, row in enumerate(csv_reader, start=1):
                try:
                    title = row['title'].strip()
                    year = int(row['year'])
                    poster_url = row['poster_url'].strip()

                    await validate_movie_input(title, year)
                    
                    movie = models.Movie(
                        title=title,
                        year=year,
                        poster_url=poster_url,
                        owner_id=user_id,
                    )
                    movies_to_add.append(movie)
                    created_count += 1
                except (ValueError, KeyError, MovieException) as e:
                    skipped_rows.append({
                        "row": index,
                        "reason": str(e)
                    })
                    continue

            if movies_to_add:
                db.add_all(movies_to_add)
                await db.commit()

        return {
            "status": "success",
            "created": created_count,
            "skipped": skipped_rows
        }
    except Exception as e:
        await db.rollback()
        raise MovieException(
            status_code=500,
            detail=f"Failed to process CSV file: {str(e)}"
        )
    finally:
        await file.close()

@router.get("/", response_model=schemas.PaginatedMovieOut)
async def get_movies(
    request: Request,
    skip: int = 0,
    limit: int = DEFAULT_PAGE_SIZE,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """Get paginated list of movies"""
    try:
        # Validate pagination parameters
        if skip < 0:
            raise MovieException(status_code=400, detail="Skip value cannot be negative")
        if limit < 1:
            raise MovieException(status_code=400, detail="Limit must be at least 1")
        if limit > MAX_PAGE_SIZE:
            raise MovieException(status_code=400, detail=f"Limit cannot exceed {MAX_PAGE_SIZE}")

        # Get total count
        count_stmt = select(func.count()).select_from(models.Movie).where(
            models.Movie.owner_id == user_id
        )
        total = await db.scalar(count_stmt) or 0

        if total == 0:
            return {"count": 0, "data": [], "totalPages": 0}

        # Fetch paginated movies
        stmt = (
            select(models.Movie)
            .where(models.Movie.owner_id == user_id)
            .order_by(models.Movie.created_at.desc())
            .limit(limit)
            .offset(skip)
        )
        result = await db.execute(stmt)
        movies = result.scalars().all()

        # Transform movies to include full URLs and ensure datetime fields
        transformed_movies = [
            transform_movie_response(movie, request) for movie in movies
        ]

        return {
            "count": total,
            "data": transformed_movies,
            "totalPages": math.ceil(total / limit)
        }
    except SQLAlchemyError as e:
        raise MovieException(status_code=500, detail="Failed to fetch movies")

@router.get("/{movie_id}", response_model=schemas.MovieOut)
async def get_movie_by_id(
    movie_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """Get a specific movie by ID"""
    movie = await get_movie_by_id_and_owner(movie_id, user_id, db)
    return transform_movie_response(movie, request)

@router.patch("/{movie_id}", response_model=schemas.MovieOut)
async def update_movie(
    movie_id: UUID,
    request: Request,
    background_tasks: BackgroundTasks,
    title: Optional[str] = Form(None),
    year: Optional[int] = Form(None),
    poster: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """Update a movie"""
    try:
        movie = await get_movie_by_id_and_owner(movie_id, user_id, db)
        
        if title is not None:
            await validate_movie_input(title, movie.year)
            movie.title = title.strip()
        
        if year is not None:
            await validate_movie_input(movie.title, year)
            movie.year = year
        
        if poster:
            old_poster_path = Path(movie.poster_url)
            new_poster_path = await save_poster_file(poster, background_tasks)
            movie.poster_url = new_poster_path
            if old_poster_path.exists():
                background_tasks.add_task(old_poster_path.unlink)
        
        movie.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(movie)
        
        return transform_movie_response(movie, request)
    except SQLAlchemyError as e:
        await db.rollback()
        raise MovieException(status_code=500, detail="Failed to update movie")

@router.delete("/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(
    movie_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """Delete a movie"""
    try:
        movie = await get_movie_by_id_and_owner(movie_id, user_id, db)
        poster_path = Path(movie.poster_url)
        
        await db.delete(movie)
        await db.commit()
        
        if poster_path.exists():
            background_tasks.add_task(poster_path.unlink)
            
        return {"status": "success", "message": "Movie deleted successfully"}
    except SQLAlchemyError as e:
        await db.rollback()
        raise MovieException(status_code=500, detail="Failed to delete movie")
