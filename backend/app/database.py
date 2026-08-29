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

engine = create_engine(settings.database_url, **engine_kwargs)
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
    """Creates database tables and seeds initial sample problem data if database is empty."""
    from app.models.problem import Problem
    from app.models.testcase import TestCase
    from app.models.submission import Submission

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if db.query(Problem).count() == 0:
            # Seed default Problem 1: Two Sum / Add Two Numbers
            p1 = Problem(
                id=1,
                title="Sum of Two Numbers",
                description="Write a program that takes two space-separated integers from stdin and prints their sum to stdout.",
                input_description="Two integers a and b separated by a space.",
                output_description="Single integer representing a + b.",
                time_limit_ms=2000,
                memory_limit_mb=256,
            )
            db.add(p1)
            db.flush()

            # Seed Sample TestCase (is_sample = True)
            tc_sample = TestCase(
                problem_id=p1.id,
                input="2 3\n",
                expected_output="5\n",
                is_sample=True,
            )

            # Seed Hidden TestCase (is_sample = False)
            tc_hidden = TestCase(
                problem_id=p1.id,
                input="10 20\n",
                expected_output="30\n",
                is_sample=False,
            )

            db.add_all([tc_sample, tc_hidden])
            db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
