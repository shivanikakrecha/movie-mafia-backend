import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
# from app.database import Base, engine
from app.routes import auth_routes, movie_routes

# Base.metadata.create_all(bind=engine)

from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
app.include_router(auth_routes.router)
app.include_router(movie_routes.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the directory for static files
STATIC_DIR = "static"
IMAGES_DIR = os.path.join(STATIC_DIR, "images")

# Create the images directory if it doesn't exist
os.makedirs(IMAGES_DIR, exist_ok=True)

# Mount the static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# from fastapi import FastAPI
# from fastapi.staticfiles import StaticFiles
# from app.database import Base, async_engine
# from app.routes import auth_routes, movie_routes
# import asyncio

# app = FastAPI()

# @app.on_event("startup")
# async def on_startup():
#     async with async_engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)

# app.include_router(auth_routes.router)
# app.include_router(movie_routes.router)
# app.mount("/static", StaticFiles(directory="static"), name="static")
