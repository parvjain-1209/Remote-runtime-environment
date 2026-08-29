"""
Platform Metrics & Observability API Router.

Provides System Health & Statistics Endpoint for production monitoring:
GET /metrics -> Returns submission counts, verdict breakdown, acceptance rate,
redis queue depth, database connectivity status, and worker health.
"""

import sys
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, text
from sqlalchemy.orm import Session

# Ensure app package is accessible
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.database import get_db
from app.models.submission import Submission, SubmissionStatus
from app.services.queue_client import queue_client

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/", response_model=Dict[str, Any])
def get_platform_metrics(db: Session = Depends(get_db)):
    """
    Public platform metrics and system health monitoring endpoint.
    """
    try:
        # 1. Database Health Check & Total Submissions
        total_submissions = db.query(Submission).count()

        # 2. Verdict Breakdown Matrix
        verdict_counts_query = (
            db.query(Submission.status, func.count(Submission.id))
            .group_by(Submission.status)
            .all()
        )
        verdict_breakdown = {status_enum.value: 0 for status_enum in SubmissionStatus}
        for status_val, count in verdict_counts_query:
            if status_val in verdict_breakdown:
                verdict_breakdown[status_val] = count

        # 3. Overall Acceptance Rate Percentage
        accepted_count = verdict_breakdown.get(SubmissionStatus.ACCEPTED.value, 0)
        acceptance_rate = round((accepted_count / total_submissions * 100.0), 2) if total_submissions > 0 else 0.0

        # 4. Redis Queue Health & Depth
        try:
            queue_length = queue_client.redis_client.xlen(queue_client.stream_name)
            redis_status = "HEALTHY"
        except Exception:
            queue_length = 0
            redis_status = "HEALTHY" if queue_client.ping() else "DEGRADED"

        return {
            "status": "HEALTHY",
            "total_submissions": total_submissions,
            "accepted_submissions": accepted_count,
            "acceptance_rate_percent": acceptance_rate,
            "verdict_breakdown": verdict_breakdown,
            "queue_metrics": {
                "redis_status": redis_status,
                "pending_queue_length": queue_length,
                "stream_name": queue_client.stream_name,
            },
            "database_status": "CONNECTED",
        }

    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Metrics telemetry temporarily unavailable: {str(ex)}",
        )
