"""
Pydantic Schemas for Problems and TestCases.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class TestCaseSample(BaseModel):
    """Schema for sample testcase visible to API clients."""
    id: int
    input: str
    expected_output: str

    model_config = ConfigDict(from_attributes=True)


class ProblemBase(BaseModel):
    title: str
    description: str
    input_description: Optional[str] = None
    output_description: Optional[str] = None
    difficulty: str = "Easy"
    tags: Optional[str] = None
    time_limit_ms: int = 2000
    memory_limit_mb: int = 256


class ProblemListItem(ProblemBase):
    """Schema for problem list view."""
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProblemDetail(ProblemBase):
    """Schema for problem detail view including sample testcases ONLY."""
    id: int
    created_at: datetime
    sample_testcases: List[TestCaseSample] = []

    model_config = ConfigDict(from_attributes=True)
