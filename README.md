# Movie Mafia Backend

A FastAPI-based backend service for managing movie collections.

## Features

- User authentication with JWT
- Movie management (CRUD operations)
- File upload for movie posters
- Search and pagination
- Role-based access control
- Input validation
- Error handling
- Database migrations
- API documentation

## Tech Stack

- **Framework**: FastAPI
- **Database**: PostgreSQL with SQLAlchemy
- **Authentication**: JWT with OAuth2
- **File Storage**: Local filesystem (configurable)
- **Documentation**: OpenAPI (Swagger) and ReDoc

## Prerequisites

- Python 3.10+
- PostgreSQL
- Poetry (optional but recommended)

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/movie-mafia-backend.git
cd movie-mafia-backend
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or
.\venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file:
```env
# Project settings
PROJECT_NAME="Movie Mafia"
VERSION="1.0.0"
API_V1_PREFIX="/api/v1"

# Security
SECRET_KEY="your-super-secret-key"  # Change this!
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database
POSTGRES_HOST=localhost
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=movie_mafia
POSTGRES_PORT=5432

# CORS
BACKEND_CORS_ORIGINS=["http://localhost:3000"]

# File Upload
UPLOAD_DIR="uploads"
MAX_UPLOAD_SIZE=5242880  # 5MB in bytes
```

5. Initialize the database:
```bash
alembic upgrade head
```

## Running the Application

1. Development server:
```bash
uvicorn app.main:app --reload
```

2. Production server:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## API Documentation

- Swagger UI: `http://localhost:8000/api/v1/docs`
- ReDoc: `http://localhost:8000/api/v1/redoc`

## Development

1. Install development dependencies:
```bash
pip install -r requirements.txt
```

2. Run tests:
```bash
pytest
```

3. Code formatting:
```bash
black .
isort .
```

4. Type checking:
```bash
mypy .
```

5. Linting:
```bash
flake8
```

## Project Structure

```
movie-mafia-backend/
├── alembic/              # Database migrations
├── app/
│   ├── core/            # Core functionality
│   │   ├── config.py    # Settings management
│   │   ├── deps.py      # Dependencies
│   │   └── security.py  # Security utilities
│   ├── models/          # SQLAlchemy models
│   ├── repositories/    # Database operations
│   ├── routes/          # API endpoints
│   ├── schemas/         # Pydantic models
│   └── main.py         # Application entry point
├── tests/              # Test suite
├── .env               # Environment variables
├── .gitignore
├── alembic.ini       # Alembic configuration
├── README.md
└── requirements.txt  # Project dependencies
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
