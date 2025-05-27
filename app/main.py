import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
# from app.database import Base, engine
from app.routes import auth_routes, movie_routes

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

# Base.metadata.create_all(bind=engine)

from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()

app.include_router(auth_routes.router, prefix='/api')
app.include_router(movie_routes.router, prefix='/api')

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Get the first error message (you can customize this logic further)
    errors = exc.errors()
    if errors:
        message = errors[0].get("msg", "Invalid input")
        if not message:
            message = errors[0].get("message", "Invalid input")
    else:
        message = "Invalid input"

    return JSONResponse(
        status_code=422,
        content={"detail": message.replace("Value error, ", "")}
    )

# Define the directory for static files
STATIC_DIR = "static"
IMAGES_DIR = os.path.join(STATIC_DIR, "images")

# Create the images directory if it doesn't exist
os.makedirs(IMAGES_DIR, exist_ok=True)

# Mount the static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")
