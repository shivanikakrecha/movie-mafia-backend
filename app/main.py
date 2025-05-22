import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.database import engine
from app.models.base import Base
from app.routes import auth_routes, movie_routes

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import get_settings

# Set up the settings
settings = get_settings()

async def create_tables():
    """Create database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        docs_url="/docs",  # Root level docs
        redoc_url="/redoc",  # Root level redoc
        openapi_url="/openapi.json"  # Root level OpenAPI schema
    )
    
    # Set up CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )
    
    # Set up trusted host middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure this properly in production
    )
    
    # Include routers with proper prefixes
    app.include_router(
        auth_routes.router,
        prefix=f"{settings.API_V1_PREFIX}/auth",
        tags=["Authentication"]
    )
    app.include_router(
        movie_routes.router,
        prefix=f"{settings.API_V1_PREFIX}/movies",
        tags=["Movies"]
    )
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy"}
    
    @app.on_event("startup")
    async def startup_event():
        """Run startup tasks."""
        await create_tables()
    
    return app

app = create_application()

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    # Get the first error message
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
