from setuptools import setup, find_packages

setup(
    name="movie-mafia",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.109.2",
        "uvicorn>=0.27.1",
        "sqlalchemy>=2.0.27",
        "asyncpg>=0.29.0",
        "alembic>=1.13.1",
        "python-jose>=3.3.0",
        "passlib>=1.7.4",
        "python-multipart>=0.0.9",
        "pydantic>=2.6.1",
        "pydantic-settings>=2.1.0",
        "email-validator>=2.1.0.post1",
    ],
) 