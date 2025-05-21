import uuid
from datetime import datetime
from sqlalchemy import (
    TIMESTAMP,
    Column,
    String,
    Boolean,
    ForeignKey,
    Integer,
    func,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from app.database import Base


# ------------------------
# User Model
# ------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    last_login: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), default=None, onupdate=func.now())

    # Relationships
    movies: Mapped[list["Movie"]] = relationship("Movie", back_populates="owner", cascade="all, delete", passive_deletes=True)


# ------------------------
# Movie Model
# ------------------------
class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    poster_url: Mapped[str] = mapped_column(Text, nullable=False)  # Assuming poster is required
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="movies")
