"""
Submission Service handling DB persistence and Redis queue dispatching.
"""

import logging
import uuid
from typing import Optional
from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.problem import Problem
from app.models.submission import Submission, SubmissionStatus
from app.schemas.submission import SubmissionCreate
from app.services.queue_client import queue_client

logger = logging.getLogger(__name__)


class SubmissionService:
    """
    Business logic for managing code submissions.
    """

    def create_submission(self, db: Session, payload: SubmissionCreate) -> Submission:
        """
        Validates problem existence, creates QUEUED submission in PostgreSQL,
        commits DB transaction, and enqueues job to Redis Stream.

        Returns:
            Created Submission ORM model instance.
        """
        # 1. Verify problem exists in database
        try:
            problem = db.query(Problem).filter(Problem.id == payload.problem_id).first()
        except SQLAlchemyError as ex:
            logger.error(f"Database error querying problem #{payload.problem_id}: {ex}")
            raise HTTPException(
                status_code=503,
                detail="Database service temporarily unavailable. Please try again later.",
            )

        if not problem:
            raise HTTPException(status_code=404, detail=f"Problem #{payload.problem_id} not found.")

        # 2. Instantiate and save submission to PostgreSQL
        submission_id = str(uuid.uuid4())
        submission = Submission(
            id=submission_id,
            problem_id=payload.problem_id,
            source_code=payload.source_code,
            language=payload.language,
            status=SubmissionStatus.QUEUED.value,
        )

        try:
            db.add(submission)
            db.commit()
            db.refresh(submission)
        except SQLAlchemyError as ex:
            db.rollback()
            logger.error(f"Database error creating submission: {ex}")
            raise HTTPException(
                status_code=503,
                detail="Database service temporarily unavailable. Please try again later.",
            )

        # 3. Enqueue submission ID to Redis Stream
        try:
            queue_client.enqueue_submission(submission_id)
        except Exception as ex:
            logger.error(f"Failed to enqueue submission '{submission_id}' to Redis: {ex}")
            # Note: Submission remains QUEUED in DB. Periodic worker recovery will pick it up safely.
            raise HTTPException(
                status_code=503,
                detail="Submission created but queue service temporarily unavailable. Job scheduled for recovery.",
            )

        return submission

    def get_submission(self, db: Session, submission_id: str) -> Optional[Submission]:
        """Fetches submission by UUID from PostgreSQL."""
        try:
            return db.query(Submission).filter(Submission.id == submission_id).first()
        except SQLAlchemyError as ex:
            logger.error(f"Database error getting submission '{submission_id}': {ex}")
            raise HTTPException(
                status_code=503,
                detail="Database service temporarily unavailable. Please try again later.",
            )


submission_service = SubmissionService()
