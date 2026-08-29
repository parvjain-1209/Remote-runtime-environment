"""
SQLAlchemy Submission Model.
"""

from enum import Enum
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class SubmissionStatus(str, Enum):
    QUEUED = "QUEUED"
    COMPILING = "COMPILING"
    RUNNING = "RUNNING"
    ACCEPTED = "ACCEPTED"
    WRONG_ANSWER = "WRONG_ANSWER"
    COMPILATION_ERROR = "COMPILATION_ERROR"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    TIME_LIMIT_EXCEEDED = "TIME_LIMIT_EXCEEDED"
    MEMORY_LIMIT_EXCEEDED = "MEMORY_LIMIT_EXCEEDED"
    OUTPUT_LIMIT_EXCEEDED = "OUTPUT_LIMIT_EXCEEDED"
    SYSTEM_ERROR = "SYSTEM_ERROR"


TERMINAL_STATUSES = {
    SubmissionStatus.ACCEPTED.value,
    SubmissionStatus.WRONG_ANSWER.value,
    SubmissionStatus.COMPILATION_ERROR.value,
    SubmissionStatus.RUNTIME_ERROR.value,
    SubmissionStatus.TIME_LIMIT_EXCEEDED.value,
    SubmissionStatus.MEMORY_LIMIT_EXCEEDED.value,
    SubmissionStatus.OUTPUT_LIMIT_EXCEEDED.value,
    SubmissionStatus.SYSTEM_ERROR.value,
}


class Submission(Base):
    """
    Submission model storing code submission details, execution metrics, and verdicts.
    """
    __tablename__ = "submissions"

    id = Column(String(36), primary_key=True)
    problem_id = Column(Integer, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    source_code = Column(Text, nullable=False)
    language = Column(String(32), nullable=False, default="cpp")
    status = Column(String(32), nullable=False, default=SubmissionStatus.QUEUED.value, index=True)
    
    execution_time_ms = Column(Float, nullable=True)
    memory_used_mb = Column(Float, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Per-testcase safe status metadata (JSON list of dicts)
    testcase_results = Column(JSON, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    problem = relationship("Problem", back_populates="submissions")
    user = relationship("User", back_populates="submissions")

    def __repr__(self) -> str:
        return f"<Submission(id='{self.id}', problem_id={self.problem_id}, status='{self.status}')>"
