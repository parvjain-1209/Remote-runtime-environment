"""
Problems API Endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.problem import Problem
from app.models.testcase import TestCase
from app.schemas.problem import ProblemDetail, ProblemListItem, TestCaseSample

router = APIRouter(prefix="/problems", tags=["problems"])


@router.get("/", response_model=List[ProblemListItem])
def list_problems(db: Session = Depends(get_db)):
    """
    Lists all available coding problems.
    """
    problems = db.query(Problem).order_by(Problem.id.asc()).all()
    return problems


@router.get("/{problem_id}", response_model=ProblemDetail)
def get_problem(problem_id: int, db: Session = Depends(get_db)):
    """
    Returns problem details and sample testcases ONLY.
    Hidden testcases are strictly filtered out.
    """
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem with ID {problem_id} not found.",
        )

    # Filter sample testcases (is_sample == True)
    sample_tcs = (
        db.query(TestCase)
        .filter(TestCase.problem_id == problem_id, TestCase.is_sample == True)
        .all()
    )

    detail = ProblemDetail(
        id=problem.id,
        title=problem.title,
        description=problem.description,
        input_description=problem.input_description,
        output_description=problem.output_description,
        time_limit_ms=problem.time_limit_ms,
        memory_limit_mb=problem.memory_limit_mb,
        created_at=problem.created_at,
        sample_testcases=[TestCaseSample.model_validate(tc) for tc in sample_tcs],
    )
    return detail
