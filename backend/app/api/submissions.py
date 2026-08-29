"""
Submissions API Router.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.submission import Submission
from app.schemas.submission import (
    SubmissionCreate,
    SubmissionListResponse,
    SubmissionResponse,
    sanitize_error_message,
)
from app.services.submission_service import submission_service

router = APIRouter(prefix="/submissions", tags=["Submissions"])


@router.post("/", response_model=SubmissionResponse, status_code=status.HTTP_201_CREATED)
def create_submission(
    payload: SubmissionCreate,
    db: Session = Depends(get_db),
):
    """
    Creates a new code submission, stores it in PostgreSQL, and enqueues job to Redis Stream.
    """
    submission = submission_service.create_submission(db=db, payload=payload)
    
    # Build sanitized response
    return SubmissionResponse(
        id=submission.id,
        problem_id=submission.problem_id,
        language=submission.language,
        status=submission.status,
        execution_time_ms=submission.execution_time_ms,
        memory_used_mb=submission.memory_used_mb,
        error_message=sanitize_error_message(submission.status, submission.error_message),
        testcase_results=submission.testcase_results,
        created_at=submission.created_at,
        completed_at=submission.completed_at,
    )


@router.get("/{submission_id}", response_model=SubmissionResponse)
def get_submission_detail(
    submission_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieves submission status, verdict, execution metrics, and sanitized error messages by UUID.
    """
    submission = submission_service.get_submission(db=db, submission_id=submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail=f"Submission '{submission_id}' not found.")

    return SubmissionResponse(
        id=submission.id,
        problem_id=submission.problem_id,
        language=submission.language,
        status=submission.status,
        execution_time_ms=submission.execution_time_ms,
        memory_used_mb=submission.memory_used_mb,
        error_message=sanitize_error_message(submission.status, submission.error_message),
        testcase_results=submission.testcase_results,
        created_at=submission.created_at,
        completed_at=submission.completed_at,
    )


@router.get("/", response_model=SubmissionListResponse)
def list_submissions(
    problem_id: Optional[int] = Query(None, description="Filter submissions by problem ID"),
    limit: int = Query(20, ge=1, le=100, description="Number of submissions to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: Session = Depends(get_db),
):
    """
    Retrieves paginated submission history metadata without exposing source code.
    """
    try:
        query = db.query(Submission)
        if problem_id is not None:
            query = query.filter(Submission.problem_id == problem_id)

        total = query.count()
        submissions = query.order_by(Submission.created_at.desc()).offset(offset).limit(limit).all()

        resp_list = [
            SubmissionResponse(
                id=sub.id,
                problem_id=sub.problem_id,
                language=sub.language,
                status=sub.status,
                execution_time_ms=sub.execution_time_ms,
                memory_used_mb=sub.memory_used_mb,
                error_message=sanitize_error_message(sub.status, sub.error_message),
                testcase_results=sub.testcase_results,
                created_at=sub.created_at,
                completed_at=sub.completed_at,
            )
            for sub in submissions
        ]

        return SubmissionListResponse(
            submissions=resp_list,
            total=total,
            limit=limit,
            offset=offset,
        )
    except SQLAlchemyError as ex:
        raise HTTPException(
            status_code=503,
            detail="Database service temporarily unavailable. Please try again later.",
        )
