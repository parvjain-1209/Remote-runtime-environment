"""
Database Connection & Session Management.
"""

import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# Ensure database URL explicitly uses psycopg2 driver if generic scheme is passed
database_url = settings.database_url
if database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif database_url.startswith("postgresql://"):
    database_url = database_url.replace("postgresql://", "postgresql+psycopg2://", 1)
elif database_url.startswith("postgresql+psycopg://"):
    database_url = database_url.replace("postgresql+psycopg://", "postgresql+psycopg2://", 1)

pool_size = int(os.getenv("DB_POOL_SIZE", "5"))
max_overflow = int(os.getenv("DB_MAX_OVERFLOW", "10"))

# Configure engine args for SQLite compatibility during testing if specified
engine_kwargs = {}
if database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_recycle=300,
        **engine_kwargs,
    )
else:
    engine = create_engine(
        database_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,
        pool_recycle=300,
        **engine_kwargs,
    )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator:
    """Dependency for acquiring database sessions in FastAPI routes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Creates database tables and seeds initial problem catalog."""
    from app.seed import seed_problems

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        seed_problems(db)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
