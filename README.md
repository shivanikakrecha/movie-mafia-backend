# 🎬 Movie Mafia - Backend

This is the backend for **Movie Mafia**, built with **FastAPI**. It provides a robust REST API for managing movies, including single and bulk uploads, authentication, and poster handling.

---

## 🚀 Tech Stack

- Python 3.10+
- FastAPI
- SQLAlchemy (Async)
- PostgreSQL (or SQLite for dev)
- Alembic (migrations)
- JWT Authentication
- Uvicorn (ASGI server)

---

## 📂 Project Structure

```
.
├── alembic/
│   ├── versions/
│   │   └── migrations          # Alembic migrations
│   └── env.py                  # Database migration environment
├── app/
│   ├── routes/                 # API route handlers
│   │   ├── auth_routes.py      # Authentication routes
│   │   └── movie_routes.py     # Movie routes
│   ├── models.py               # SQLAlchemy models
│   ├── database.py             # Async DB connection
│   ├── schemas/                # Pydantic schemas
│   └── main.py                 # App entry point
├── alembic.ini                 # Alembic config
├── .env                        # Environment variables
└── requirements.txt            # Python dependencies
```

---

## 🛠️ Setup & Installation

### 1. Clone the repo

```bash
git clone https://github.com/shivanikakrecha/movie-mafia-backend
cd movie-mafia-backend
```

### 2. Create and activate virtual environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create `.env` file and add the following:

```env
SECRET_KEY=09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DATABASE_URL=postgresql+asyncpg://movieuser:Success%40321@localhost/moviedb
```

### 5. Run database migrations

```bash
alembic revision --autogenerate -m "create user and movie tables"
alembic upgrade head
```

### 6. Run the development server

```bash
uvicorn app.main:app --reload
```

---

## 📦 Features

✅ JWT Auth (Login / Signup)  
✅ Movie CRUD APIs  
✅ Poster support  
✅ Bulk upload via CSV  
✅ Async database support  

---

## 📮 API Documentation

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)  
- Redoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)