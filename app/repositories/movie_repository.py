from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.movie import Movie
from app.repositories.base import BaseRepository
from app.schemas.movie import MovieCreate, MovieUpdate

class MovieRepository(BaseRepository[Movie, MovieCreate, MovieUpdate]):
    """Movie repository for database operations."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Movie, db)
    
    async def get_movies_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None
    ) -> tuple[list[Movie], int]:
        """
        Get movies for a specific user with pagination and search.
        
        Args:
            user_id: User ID
            skip: Number of records to skip
            limit: Maximum number of records to return
            search: Optional search term for movie title
            
        Returns:
            Tuple of (list of movies, total count)
        """
        query = select(Movie).where(Movie.owner_id == user_id)
        
        if search:
            query = query.where(Movie.title.ilike(f"%{search}%"))
            
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)
        
        # Get paginated results
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        movies = result.scalars().all()
        
        return movies, total
    
    async def create_movie(
        self,
        obj_in: MovieCreate,
        user_id: UUID
    ) -> Movie:
        """
        Create a new movie for a user.
        
        Args:
            obj_in: Movie creation data
            user_id: User ID who owns the movie
            
        Returns:
            Created movie instance
        """
        now = datetime.utcnow()
        db_obj = Movie(
            **obj_in.model_dump(),
            owner_id=user_id,
            created_at=now,
            updated_at=now
        )
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj
    
    async def update_movie(
        self,
        *,
        db_obj: Movie,
        obj_in: MovieUpdate
    ) -> Movie:
        """
        Update a movie.
        
        Args:
            db_obj: Existing movie instance
            obj_in: Movie update data
            
        Returns:
            Updated movie instance
        """
        update_data = obj_in.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        
        return await super().update(db_obj=db_obj, obj_in=update_data)
    
    async def get_movie_with_owner(self, movie_id: UUID) -> Optional[Movie]:
        """
        Get a movie with its owner information.
        
        Args:
            movie_id: Movie ID
            
        Returns:
            Movie instance with owner loaded or None
        """
        query = (
            select(Movie)
            .options(joinedload(Movie.owner))
            .where(Movie.id == movie_id)
        )
        result = await self.db.execute(query)
        return result.unique().scalar_one_or_none() 