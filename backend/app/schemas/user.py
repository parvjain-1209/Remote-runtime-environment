"""
Pydantic Schemas for User Authentication & User Statistics.
"""

from datetime import datetime
from typing import Dict
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    username: str | None = None
    user_id: int | None = None


class UserStatsResponse(BaseModel):
    user: UserResponse
    total_submissions: int
    total_solved_problems: int
    total_attempted_problems: int
    acceptance_rate: float
    solved_by_difficulty: Dict[str, int]
    total_by_difficulty: Dict[str, int]
    verdict_counts: Dict[str, int]
