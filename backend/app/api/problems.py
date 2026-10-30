"""
Problems API Endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.rbac import require_roles
from app.database import get_db
from app.models.problem import Problem
from app.models.testcase import TestCase
from app.models.user import User
from app.schemas.problem import (
    ProblemCreate,
    ProblemDetail,
    ProblemListItem,
    ProblemUpdate,
    TestCaseSample,
)

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
        difficulty=problem.difficulty,
        tags=problem.tags,
        time_limit_ms=problem.time_limit_ms,
        memory_limit_mb=problem.memory_limit_mb,
        created_at=problem.created_at,
        sample_testcases=[TestCaseSample.model_validate(tc) for tc in sample_tcs],
    )
    return detail


@router.post("/", response_model=ProblemDetail, status_code=status.HTTP_201_CREATED)
def create_problem(
    problem_in: ProblemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("instructor", "admin")),
):
    """
    Creates a new problem. Requires instructor or admin role.
    """
    problem = Problem(
        title=problem_in.title,
        description=problem_in.description,
        input_description=problem_in.input_description,
        output_description=problem_in.output_description,
        difficulty=problem_in.difficulty,
        tags=problem_in.tags,
        time_limit_ms=problem_in.time_limit_ms,
        memory_limit_mb=problem_in.memory_limit_mb,
    )
    db.add(problem)
    db.commit()
    db.refresh(problem)

    return ProblemDetail(
        id=problem.id,
        title=problem.title,
        description=problem.description,
        input_description=problem.input_description,
        output_description=problem.output_description,
        difficulty=problem.difficulty,
        tags=problem.tags,
        time_limit_ms=problem.time_limit_ms,
        memory_limit_mb=problem.memory_limit_mb,
        created_at=problem.created_at,
        sample_testcases=[],
    )


@router.put("/{problem_id}", response_model=ProblemDetail)
def update_problem(
    problem_id: int,
    problem_in: ProblemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("instructor", "admin")),
):
    """
    Updates an existing problem (partial update allowed). Requires instructor or admin role.
    """
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem with ID {problem_id} not found.",
        )

    update_data = problem_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(problem, field, value)

    db.commit()
    db.refresh(problem)

    sample_tcs = (
        db.query(TestCase)
        .filter(TestCase.problem_id == problem_id, TestCase.is_sample == True)
        .all()
    )

    return ProblemDetail(
        id=problem.id,
        title=problem.title,
        description=problem.description,
        input_description=problem.input_description,
        output_description=problem.output_description,
        difficulty=problem.difficulty,
        tags=problem.tags,
        time_limit_ms=problem.time_limit_ms,
        memory_limit_mb=problem.memory_limit_mb,
        created_at=problem.created_at,
        sample_testcases=[TestCaseSample.model_validate(tc) for tc in sample_tcs],
    )


@router.delete("/{problem_id}", status_code=status.HTTP_200_OK)
def delete_problem(
    problem_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("instructor", "admin")),
):
    """
    Deletes an existing problem. Requires instructor or admin role.
    """
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Problem with ID {problem_id} not found.",
        )

    db.delete(problem)
    db.commit()
    return {"detail": f"Problem {problem_id} deleted successfully."}
