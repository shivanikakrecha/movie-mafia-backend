from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
import logging

from app.core.config import get_settings
from app.models import Base

settings = get_settings()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log the database URL (with password masked)
db_url = settings.get_database_uri()
masked_url = db_url.replace(settings.POSTGRES_PASSWORD.get_secret_value(), "****")
logger.info(f"Connecting to database: {masked_url}")

# Create async engine
engine = create_async_engine(
    db_url,
    echo=settings.DB_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_pre_ping=True
)

# Create session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Database dependency
async def get_db() -> AsyncSession:
    """Get a database session."""
    async with AsyncSessionLocal() as session:
        try:
            # Test the connection
            await session.execute(text("SELECT 1"))
            yield session
        except SQLAlchemyError as e:
            logger.error(f"Database error: {str(e)}")
            await session.rollback()
            raise
        finally:
            await session.close()

# For backwards compatibility
get_session = get_db
