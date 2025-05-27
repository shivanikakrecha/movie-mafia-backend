import csv
from datetime import datetime
import io
import math
import os
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID

from fastapi import (
    APIRouter, Depends, File, Form, UploadFile,
    HTTPException, status, BackgroundTasks, Request
)
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
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
MEDIA_DIR = Path("media/posters")
MAX_TITLE_LENGTH = 100
MIN_YEAR = 1888
DEFAULT_PAGE_SIZE = 8
MAX_PAGE_SIZE = 100
MAX_BULK_INSERT_SIZE = 1000

# Error Messages
ERROR_MESSAGES = {
    "INVALID_TOKEN": "Could not validate credentials",
    "FILE_TOO_LARGE": lambda size: f"File size exceeds {size // (1024 * 1024)} MB limit",
    "INVALID_FILE_TYPE": lambda types: f"Unsupported file type. Allowed types: {', '.join(types)}",
    "TITLE_LENGTH": f"Title must be between 1 and {MAX_TITLE_LENGTH} characters",
    "INVALID_YEAR": lambda current_year: f"Year must be between {MIN_YEAR} and {current_year}",
    "MOVIE_NOT_FOUND": "Movie not found",
    "DB_ERROR": "Database error occurred",
    "BULK_SIZE_EXCEEDED": f"Bulk upload size cannot exceed {MAX_BULK_INSERT_SIZE} records",
    "INVALID_CSV": "Invalid CSV format or missing required fields",
}

class MovieException(HTTPException):
    """Custom exception for movie-related errors with logging capability"""
    def __init__(self, status_code: int, detail: str, log_error: bool = True):
        super().__init__(status_code=status_code, detail=detail)
        if log_error:
            # In a production environment, you would want to use proper logging
            print(f"MovieException: {status_code} - {detail}")

class FileHandler:
    """Handle file operations with proper error handling and cleanup"""
    
    @staticmethod
    async def validate_file_type(file: UploadFile) -> None:
        if not file.filename:
            raise MovieException(status_code=400, detail="No filename provided")
        
        if file.content_type not in ALLOWED_IMAGE_TYPES:
            raise MovieException(
                status_code=400,
                detail=ERROR_MESSAGES["INVALID_FILE_TYPE"](ALLOWED_IMAGE_TYPES)
            )

    @staticmethod
    def generate_safe_filename(original_filename: str) -> str:
        """Generate a safe filename with timestamp"""
        timestamp = datetime.now().timestamp()
        safe_name = "".join(c if c.isalnum() or c in "._- " else "_" for c in original_filename)
        return f"{timestamp}_{safe_name.replace(' ', '_')}"

    @staticmethod
    async def save_file(
        file: UploadFile,
        background_tasks: BackgroundTasks,
        max_size: int = MAX_FILE_SIZE
    ) -> Tuple[str, Path]:
        """Save file with size validation and cleanup on failure"""
        try:
            # POSTER_DIR.mkdir(parents=True, exist_ok=True)
            # safe_filename = FileHandler.generate_safe_filename(file.filename)
            # file_path = POSTER_DIR / safe_filename

            MEDIA_DIR.mkdir(parents=True, exist_ok=True)
            safe_filename = FileHandler.generate_safe_filename(file.filename)
            file_path = MEDIA_DIR / safe_filename
            
            total_size = 0
            with file_path.open("wb") as buffer:
                while chunk := await file.read(CHUNK_SIZE):
                    total_size += len(chunk)
                    if total_size > max_size:
                        background_tasks.add_task(file_path.unlink)
                        raise MovieException(
                            status_code=413,
                            detail=ERROR_MESSAGES["FILE_TOO_LARGE"](max_size)
                        )
                    buffer.write(chunk)
            
            return str(file_path), file_path
        except Exception as e:
            if 'file_path' in locals() and file_path.exists():
                background_tasks.add_task(file_path.unlink)
            if isinstance(e, MovieException):
                raise
            raise MovieException(
                status_code=500,
                detail=f"Failed to save file: {str(e)}"
            )
        finally:
            await file.close()

class MovieValidator:
    """Validate movie-related data"""
    
    @staticmethod
    async def validate_title_and_year(title: str, year: int) -> None:
        if not title or not (1 <= len(title.strip()) <= MAX_TITLE_LENGTH):
            raise MovieException(status_code=400, detail=ERROR_MESSAGES["TITLE_LENGTH"])
        
        current_year = datetime.now().year
        if not (MIN_YEAR <= year <= current_year):
            raise MovieException(
                status_code=400,
                detail=ERROR_MESSAGES["INVALID_YEAR"](current_year)
            )

    @staticmethod
    def transform_response(movie: models.Movie, request: Request) -> Dict[str, Any]:
        """Transform movie model to response format"""
        return {
            "id": movie.id,
            "title": movie.title,
            "year": movie.year,
            "poster_url": movie.poster_url if movie.poster_url.startswith('http') else get_full_url(request, movie.poster_url),
            "owner_id": movie.owner_id,
            "created_at": movie.created_at or datetime.utcnow(),
            "updated_at": movie.updated_at or datetime.utcnow()
        }

class DatabaseOperations:
    """Handle database operations with proper error handling"""
    
    @staticmethod
    async def get_movie_by_id_and_owner(
        movie_id: UUID,
        user_id: UUID,
        db: AsyncSession
    ) -> models.Movie:
        try:
            result = await db.execute(
                select(models.Movie).where(
                    and_(
                        models.Movie.id == movie_id,
                        models.Movie.owner_id == user_id
                    )
                )
            )
            movie = result.scalar_one_or_none()
            if not movie:
                raise MovieException(
                    status_code=404,
                    detail=ERROR_MESSAGES["MOVIE_NOT_FOUND"]
                )
            return movie
        except SQLAlchemyError as e:
            raise MovieException(
                status_code=500,
                detail=ERROR_MESSAGES["DB_ERROR"]
            )

    @staticmethod
    async def commit_with_rollback(db: AsyncSession, error_msg: str = "Database error") -> None:
        try:
            await db.commit()
        except IntegrityError as e:
            await db.rollback()
            raise MovieException(status_code=409, detail=f"Integrity error: {str(e)}")
        except SQLAlchemyError as e:
            await db.rollback()
            raise MovieException(status_code=500, detail=error_msg)

async def get_current_user(token: str = Depends(oauth2_scheme)) -> UUID:
    """Validate JWT token and return user ID"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = UUID(payload.get("sub"))
        if not user_id:
            raise MovieException(status_code=401, detail="Invalid token payload")
        return user_id
    except (JWTError, ValueError):
        raise MovieException(
            status_code=401,
            detail=ERROR_MESSAGES["INVALID_TOKEN"]
        )

def get_full_url(request: Request, path: str) -> str:
    """Convert relative path to full URL"""
    base_url = str(request.base_url).rstrip('/')
    path = str(path).lstrip('/')
    return f"{base_url}/{path}"

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
        # Validate inputs
        await MovieValidator.validate_title_and_year(title, year)
        await FileHandler.validate_file_type(poster)
        
        # Save poster file
        poster_path, file_path = await FileHandler.save_file(poster, background_tasks)
        
        # Create movie record
        now = datetime.utcnow()
        new_movie = models.Movie(
            title=title.strip(),
            year=year,
            poster_url=poster_path,
            owner_id=user_id,
            created_at=now,
            updated_at=now
        )
        
        try:
            db.add(new_movie)
            await DatabaseOperations.commit_with_rollback(db, "Failed to create movie")
            await db.refresh(new_movie)
            return MovieValidator.transform_response(new_movie, request)
        except Exception as e:
            background_tasks.add_task(file_path.unlink)
            raise
    except Exception as e:
        if isinstance(e, MovieException):
            raise
        raise MovieException(status_code=500, detail=str(e))

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
                detail=ERROR_MESSAGES["INVALID_CSV"]
            )

        movies_to_add = []
        errors = []
        now = datetime.utcnow()

        for index, row in enumerate(csv_reader, start=1):
            if index > MAX_BULK_INSERT_SIZE:
                raise MovieException(
                    status_code=400,
                    detail=ERROR_MESSAGES["BULK_SIZE_EXCEEDED"]
                )

            try:
                title = row['title'].strip()
                year = int(row['year'])
                poster_url = row['poster_url'].strip()

                await MovieValidator.validate_title_and_year(title, year)
                
                movies_to_add.append(models.Movie(
                    title=title,
                    year=year,
                    poster_url=poster_url,
                    owner_id=user_id,
                    created_at=now,
                    updated_at=now
                ))
            except Exception as e:
                errors.append({
                    "row": index,
                    "reason": str(e)
                })

        if movies_to_add:
            try:
                db.add_all(movies_to_add)
                await DatabaseOperations.commit_with_rollback(
                    db,
                    "Failed to save movies to database"
                )
            except Exception as e:
                errors.append({
                    "row": "database",
                    "reason": str(e)
                })
                raise

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "status": "success",
                "created": len(movies_to_add),
                "errors": errors
            }
        )
    except Exception as e:
        if isinstance(e, MovieException):
            raise
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
        if not (1 <= limit <= MAX_PAGE_SIZE):
            raise MovieException(
                status_code=400,
                detail=f"Limit must be between 1 and {MAX_PAGE_SIZE}"
            )

        # Get total count efficiently
        count_stmt = select(func.count()).select_from(models.Movie).where(
            models.Movie.owner_id == user_id
        )
        total = await db.scalar(count_stmt) or 0

        if total == 0:
            return {"count": 0, "data": [], "totalPages": 0}

        # Fetch paginated movies efficiently
        stmt = (
            select(models.Movie)
            .where(models.Movie.owner_id == user_id)
            .order_by(models.Movie.created_at.desc())
            .limit(limit)
            .offset(skip)
        )
        
        # Execute query and transform results
        result = await db.execute(stmt)
        movies = result.scalars().all()
        transformed_movies = [
            MovieValidator.transform_response(movie, request)
            for movie in movies
        ]

        return {
            "count": total,
            "data": transformed_movies,
            "totalPages": math.ceil(total / limit)
        }
    except SQLAlchemyError as e:
        raise MovieException(
            status_code=500,
            detail="Failed to fetch movies"
        )

@router.get("/{movie_id}", response_model=schemas.MovieOut)
async def get_movie_by_id(
    movie_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """Get a specific movie by ID"""
    movie = await DatabaseOperations.get_movie_by_id_and_owner(movie_id, user_id, db)
    return MovieValidator.transform_response(movie, request)

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
        movie = await DatabaseOperations.get_movie_by_id_and_owner(movie_id, user_id, db)
        
        if title is not None or year is not None:
            new_title = title if title is not None else movie.title
            new_year = year if year is not None else movie.year
            await MovieValidator.validate_title_and_year(new_title, new_year)
            movie.title = new_title.strip()
            movie.year = new_year
        
        if poster:
            await FileHandler.validate_file_type(poster)
            old_poster_path = Path(movie.poster_url)
            new_poster_path, file_path = await FileHandler.save_file(poster, background_tasks)
            movie.poster_url = new_poster_path
            if old_poster_path.exists():
                background_tasks.add_task(old_poster_path.unlink)
        
        movie.updated_at = datetime.utcnow()
        await DatabaseOperations.commit_with_rollback(db, "Failed to update movie")
        await db.refresh(movie)
        
        return MovieValidator.transform_response(movie, request)
    except Exception as e:
        if isinstance(e, MovieException):
            raise
        raise MovieException(status_code=500, detail=str(e))

@router.delete("/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(
    movie_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    """Delete a movie"""
    try:
        movie = await DatabaseOperations.get_movie_by_id_and_owner(movie_id, user_id, db)
        poster_path = Path(movie.poster_url)
        
        await db.delete(movie)
        await DatabaseOperations.commit_with_rollback(db, "Failed to delete movie")
        
        if poster_path.exists():
            background_tasks.add_task(poster_path.unlink)
        
        return JSONResponse(
            status_code=status.HTTP_204_NO_CONTENT,
            content=None
        )
    except Exception as e:
        if isinstance(e, MovieException):
            raise
        raise MovieException(status_code=500, detail=str(e))
