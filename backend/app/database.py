"""
Database Connection & Session Management.
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# Configure engine args for SQLite compatibility during testing if specified
engine_kwargs = {}
if settings.database_url.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
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
