from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app import schemas, models, database, auth
from jose import jwt, JWTError

from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Form

router = APIRouter()

@router.post("/register")
async def register(user: schemas.UserCreate, db: AsyncSession = Depends(get_db)):
    # Asynchronously check if the email already exists in the database
    stmt = select(models.User).where(models.User.email == user.email)
    result = await db.execute(stmt)
    db_user = result.scalar_one_or_none()

    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash the password
    hashed = auth.get_password_hash(user.password)
    
    # Create new user and save to the database
    new_user = models.User(email=user.email, hashed_password=hashed, created_at=datetime.utcnow())
    db.add(new_user)
    await db.commit()  # Commit the transaction asynchronously
    await db.refresh(new_user)  # Refresh to get the latest data after commit

    return {"msg": "Registered successfully"}

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = form_data.username
    password = form_data.password
    # Asynchronously check if the email exists and match the password
    stmt = select(models.User).where(models.User.email == user)
    result = await db.execute(stmt)
    db_user = result.scalar_one_or_none()

    if not db_user or not auth.verify_password(password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    # Create JWT token for the authenticated user
    token = auth.create_access_token({"sub": str(db_user.id)})
    return {"access_token": token, "token_type": "bearer"}
