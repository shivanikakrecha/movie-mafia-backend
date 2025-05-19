import uuid
from datetime import datetime, timezone
from sqlalchemy import TIMESTAMP, Column, String, Boolean, DateTime, ForeignKey, Integer, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP(timezone=True), default=func.now())
    last_login = Column(TIMESTAMP(timezone=True), default=None, onupdate=func.now())

    movies = relationship("Movie", back_populates="owner")

class Movie(Base):
    __tablename__ = "movies"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String, nullable=False)
    year = Column(Integer, nullable=False)
    poster_url = Column(String, nullable=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(TIMESTAMP(timezone=True), default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), default=func.now(), onupdate=func.now())


    owner = relationship("User", back_populates="movies")

# from sqlalchemy import Column, Integer, String
# from app.database import Base

# class User(Base):
#     __tablename__ = "users"
#     id = Column(Integer, primary_key=True, index=True)
#     email = Column(String, unique=True, index=True)
#     hashed_password = Column(String)

# class Movie(Base):
#     __tablename__ = "movies"
#     id = Column(Integer, primary_key=True, index=True)
#     title = Column(String)
#     year = Column(Integer)
#     poster = Column(String)

