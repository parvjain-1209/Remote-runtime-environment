"""
User Profile & Statistics API Routes.
"""

from typing import Dict
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.database import get_db
from app.models.problem import Problem
from app.models.submission import Submission
from app.models.user import User
from app.schemas.submission import SubmissionListResponse, SubmissionResponse
from app.schemas.user import UserResponse, UserStatsResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me/stats", response_model=UserStatsResponse)
def get_current_user_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get aggregated problem-solving statistics for the currently authenticated user.
    """
    # Fetch all submissions for the user
    user_subs = (
        db.query(Submission)
        .filter(Submission.user_id == current_user.id)
        .all()
    )

    total_submissions = len(user_subs)
    attempted_problem_ids = set()
    solved_problem_ids = set()
    verdict_counts: Dict[str, int] = {
        "ACCEPTED": 0,
        "WRONG_ANSWER": 0,
        "TIME_LIMIT_EXCEEDED": 0,
        "MEMORY_LIMIT_EXCEEDED": 0,
        "OUTPUT_LIMIT_EXCEEDED": 0,
        "COMPILATION_ERROR": 0,
        "RUNTIME_ERROR": 0,
        "SYSTEM_ERROR": 0,
    }

    for sub in user_subs:
        attempted_problem_ids.add(sub.problem_id)
        verdict_counts[sub.status] = verdict_counts.get(sub.status, 0) + 1
        if sub.status == "ACCEPTED":
            solved_problem_ids.add(sub.problem_id)

    total_solved_problems = len(solved_problem_ids)
    total_attempted_problems = len(attempted_problem_ids)

    accepted_count = verdict_counts.get("ACCEPTED", 0)
    acceptance_rate = (
        round((accepted_count / total_submissions) * 100, 1)
        if total_submissions > 0
        else 0.0
    )

    # Fetch all catalog problems for difficulty breakdown
    catalog_problems = db.query(Problem).all()
    total_by_difficulty: Dict[str, int] = {"Easy": 0, "Medium": 0, "Hard": 0}
    problem_diff_map: Dict[int, str] = {}

    for p in catalog_problems:
        diff = p.difficulty if p.difficulty in total_by_difficulty else "Easy"
        total_by_difficulty[diff] = total_by_difficulty.get(diff, 0) + 1
        problem_diff_map[p.id] = diff

    solved_by_difficulty: Dict[str, int] = {"Easy": 0, "Medium": 0, "Hard": 0}
    for pid in solved_problem_ids:
        diff = problem_diff_map.get(pid, "Easy")
        solved_by_difficulty[diff] = solved_by_difficulty.get(diff, 0) + 1

    return UserStatsResponse(
        user=UserResponse.model_validate(current_user),
        total_submissions=total_submissions,
        total_solved_problems=total_solved_problems,
        total_attempted_problems=total_attempted_problems,
        acceptance_rate=acceptance_rate,
        solved_by_difficulty=solved_by_difficulty,
        total_by_difficulty=total_by_difficulty,
        verdict_counts=verdict_counts,
    )


@router.get("/me/submissions", response_model=SubmissionListResponse)
def get_current_user_submissions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get paginated submission history strictly belonging to the currently authenticated user.
    """
    query = (
        db.query(Submission)
        .filter(Submission.user_id == current_user.id)
        .order_by(Submission.created_at.desc())
    )

    total = query.count()
    submissions = query.offset(offset).limit(limit).all()

    return SubmissionListResponse(
        submissions=[SubmissionResponse.model_validate(s) for s in submissions],
        total=total,
        limit=limit,
        offset=offset,
    )
