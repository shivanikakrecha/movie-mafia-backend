from sqlalchemy.orm import sessionmaker

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base

import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

# Create Async Engine
async_engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=True, future=True)

# Create Async Session Local
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


# Dependency to get async DB session
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker, declarative_base
# import os

# DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")

# engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base = declarative_base()