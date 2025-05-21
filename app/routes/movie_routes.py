import csv
import io
import math
import shutil
from pathlib import Path
from typing import List
from uuid import UUID

from typing import Optional
from fastapi import (
    APIRouter, Depends, File, Form, UploadFile,
    HTTPException, status
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.database import get_db
from app import models, schemas
from app.auth import SECRET_KEY, ALGORITHM
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
CHUNK_SIZE = 1024 * 1024  # 1 MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png"}
POSTER_DIR = Path("static/posters")


def get_current_user(token: str = Depends(oauth2_scheme)) -> UUID:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = UUID(payload.get("sub"))
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        return user_id
    except (JWTError, ValueError):
        raise HTTPException(status_code=401, detail="Could not validate credentials")


def save_poster_file(poster: UploadFile) -> str:
    if poster.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    POSTER_DIR.mkdir(parents=True, exist_ok=True)
    file_path = POSTER_DIR / poster.filename

    # Avoid name collision
    suffix = 1
    while file_path.exists():
        file_path = POSTER_DIR / f"{file_path.stem}_{suffix}{file_path.suffix}"
        suffix += 1

    # Write in chunks and track size
    total_size = 0
    try:
        with file_path.open("wb") as buffer:
            while True:
                chunk = poster.file.read(CHUNK_SIZE)
                if not chunk:
                    break
                total_size += len(chunk)
                if total_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=f"Poster file size exceeds {MAX_FILE_SIZE // (1024 * 1024)} MB limit.",
                    )
                buffer.write(chunk)
    finally:
        poster.file.close()

    return str(file_path)


router = APIRouter(
    prefix="/movies",
    tags=["Movies"],
    dependencies=[Depends(get_current_user)]
)



@router.post("/bulk-upload/")
async def bulk_upload_movies(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    try:
        contents = await file.read()
        decoded = contents.decode("utf-8")
        csv_reader = csv.DictReader(io.StringIO(decoded))
    except Exception as e:
        print(f"Failed to read or decode file: {e}")
        raise HTTPException(status_code=400, detail="Invalid CSV file format")

    created_count = 0
    skipped_rows = []

    async with db.begin():
        for index, row in enumerate(csv_reader, start=1):
            title = row.get("title")
            year = row.get("year")
            poster_url = row.get("poster_url")

            if not title or not year or not poster_url:
                skipped_rows.append({"row": index, "reason": "Missing required fields"})
                continue

            try:
                year = int(year)
            except ValueError:
                skipped_rows.append({"row": index, "reason": "Year must be an integer"})
                continue

            movie = models.Movie(
                title=title.strip(),
                year=year,
                poster_url=poster_url.strip(),
                owner_id=user_id
            )

            db.add(movie)
            created_count += 1

    try:
        await db.commit()
    except Exception as e:
        print(f"Database commit failed: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save movies to the database")

    return {
        "status": "success",
        "created": created_count,
        "skipped": skipped_rows
    }


async def create_movie(
    title: Optional[str] = Form(None),
    year: Optional[int] = Form(None),
    poster: Optional[UploadFile] = File(None),
    csv_file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    movies = []

    # ✅ Bulk upload via CSV
    if csv_file:
        content = await csv_file.read()
        decoded = content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(decoded))

        for row in reader:
            try:
                row_title = row["title"].strip()
                row_year = int(row["year"])
                row_poster = row["poster_path"].strip()

                if row_year < 1888 or row_year > 2100:
                    raise ValueError("Invalid year")

                movie = models.Movie(
                    title=row_title,
                    year=row_year,
                    poster_url=row_poster,
                    owner_id=user_id
                )
                db.add(movie)
                movies.append(movie)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"CSV Error: {str(e)}")

        await db.commit()
        for movie in movies:
            await db.refresh(movie)

        return movies

    # ✅ Single movie upload
    if not title or not year or not poster:
        raise HTTPException(status_code=400, detail="Missing title, year, or poster")

    if year < 1888 or year > 2100:
        raise HTTPException(status_code=400, detail="Invalid year value")

    poster_path = save_poster_file(poster)

    movie = models.Movie(
        title=title,
        year=year,
        poster_url=poster_path,
        owner_id=user_id
    )
    db.add(movie)
    await db.commit()
    await db.refresh(movie)

    return [movie]


@router.get("/", response_model=schemas.PaginatedMovieOut)
async def get_movies(
    skip: int = 0,
    limit: int = 8,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    stmt = (
        select(models.Movie, func.count().over())
        .where(models.Movie.owner_id == user_id)
        .limit(limit)
        .offset(skip)
    )

    result = await db.execute(stmt)
    rows = result.all()

    if not rows:
        return {"count": 0, "data": [], "totalPages": 0}

    movies = [row[0] for row in rows]
    total = rows[0][1]

    return {
        "count": total,
        "data": movies,
        "totalPages": math.ceil(total / limit)
    }


@router.get("/{movie_id}", response_model=schemas.MovieOut)
async def get_movie_by_id(
    movie_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Movie).where(
            models.Movie.id == movie_id,
            models.Movie.owner_id == user_id
        )
    )
    movie = result.scalar_one_or_none()

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    return movie


@router.patch("/{movie_id}", response_model=schemas.MovieOut)
async def update_movie(
    movie_id: UUID,
    title: str = Form(...),
    year: int = Form(...),
    poster: UploadFile = File(None),
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    if year < 1888 or year > 2100:
        raise HTTPException(status_code=400, detail="Invalid year value")

    result = await db.execute(
        select(models.Movie).where(
            models.Movie.id == movie_id,
            models.Movie.owner_id == user_id
        )
    )
    movie = result.scalar_one_or_none()

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    movie.title = title
    movie.year = year

    if poster:
        movie.poster_url = save_poster_file(poster)

    await db.commit()
    await db.refresh(movie)
    return movie


@router.delete("/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(
    movie_id: UUID,
    db: AsyncSession = Depends(get_db),
    user_id: UUID = Depends(get_current_user),
):
    result = await db.execute(
        select(models.Movie).where(
            models.Movie.id == movie_id,
            models.Movie.owner_id == user_id
        )
    )
    movie = result.scalar_one_or_none()

    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")

    await db.delete(movie)
    await db.commit()

    return {"msg": "Movie deleted successfully"}
