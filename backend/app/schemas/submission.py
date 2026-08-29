"""
Pydantic Schemas for Submission API.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class SubmissionCreate(BaseModel):
    """Schema for submitting C++, Python, or Java solution."""
    problem_id: int = Field(..., description="ID of the problem being solved")
    language: str = Field(..., description="Programming language (cpp, python, java)")
    source_code: str = Field(..., description="Source code string")

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if v_clean in ["cpp", "c++"]:
            return "cpp"
        if v_clean in ["python", "python3", "py"]:
            return "python"
        if v_clean in ["java"]:
            return "java"
        raise ValueError("Unsupported language. Supported languages: 'cpp', 'python', 'java'.")

    @field_validator("source_code")
    @classmethod
    def validate_source_code(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Source code cannot be empty.")
        code_bytes = v.encode("utf-8")
        if len(code_bytes) > 64 * 1024:
            raise ValueError(f"Source code size ({len(code_bytes)} bytes) exceeds max limit of 64 KB.")
        return v


class TestCaseResultSummary(BaseModel):
    """Safe metadata summary for an individual testcase execution."""
    testcase_index: int
    status: str
    duration_ms: float


def sanitize_error_message(status: str, raw_msg: Optional[str]) -> Optional[str]:
    """
    Sanitizes raw backend error messages so filesystem paths, Docker internals,
    Python tracebacks, and database strings are NEVER exposed to clients.
    """
    if not raw_msg and status not in ["COMPILATION_ERROR", "RUNTIME_ERROR", "SYSTEM_ERROR"]:
        return None

    if status == "COMPILATION_ERROR":
        if raw_msg:
            lines = [line for line in raw_msg.splitlines() if not line.startswith("Compilation failed inside Docker")]
            clean_text = "\n".join(lines).strip()
            return clean_text if clean_text else "Compilation failed."
        return "Compilation failed."

    if status == "RUNTIME_ERROR":
        return "Runtime error occurred during execution."

    if status == "TIME_LIMIT_EXCEEDED":
        return "Time limit exceeded."

    if status == "MEMORY_LIMIT_EXCEEDED":
        return "Memory limit exceeded."

    if status == "OUTPUT_LIMIT_EXCEEDED":
        return "Output limit exceeded."

    if status == "SYSTEM_ERROR":
        return "Judge system error. Please try again later."

    return None


class SubmissionResponse(BaseModel):
    """Schema for submission response and verdict retrieval."""
    id: str
    problem_id: int
    language: str
    status: str
    execution_time_ms: Optional[float] = None
    memory_used_mb: Optional[float] = None
    error_message: Optional[str] = None
    testcase_results: Optional[List[TestCaseResultSummary]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SubmissionListResponse(BaseModel):
    """Schema for paginated submission history list."""
    submissions: List[SubmissionResponse]
    total: int
    limit: int
    offset: int
