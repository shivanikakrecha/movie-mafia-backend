from functools import lru_cache
from typing import Optional, List

from pydantic import PostgresDsn, SecretStr, Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings management using Pydantic."""
    
    # Project Metadata
    PROJECT_NAME: str = "Movie Mafia"
    VERSION: str = "1.0.0"
    API_V1_PREFIX: str = "/api/v1"
    
    # Security
    SECRET_KEY: SecretStr = Field(
        default="09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database Configuration
    DATABASE_URL: Optional[str] = None
    POSTGRES_HOST: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: SecretStr = Field(default=SecretStr("postgres"))
    POSTGRES_DB: str = "moviedb"
    POSTGRES_PORT: int = 5432
    
    # Database Connection Settings
    DB_ECHO: bool = False  # SQL query logging
    DB_POOL_SIZE: int = 5  # Number of connections to keep open
    DB_MAX_OVERFLOW: int = 10  # Max number of connections above pool_size
    DB_POOL_TIMEOUT: int = 30  # Seconds to wait for a connection from pool
    
    # CORS
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # File Upload
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE: int = 5_242_880  # 5MB in bytes
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp"]
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Cache
    REDIS_URL: Optional[str] = None
    CACHE_EXPIRE_IN_SECONDS: int = 300  # 5 minutes
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )
    
    def get_database_uri(self) -> str:
        """Construct database URI from components or return existing URL."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
            
        # Construct the database URL manually to ensure correct formatting
        password = self.POSTGRES_PASSWORD.get_secret_value()
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{password}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


@lru_cache
def get_settings() -> Settings:
    """Create cached settings instance."""
    return Settings()