from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import DifficultyEnum
from app.schemas.test_case import TestCasePublicResponse, TestCaseResponse


class ProblemCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10)
    difficulty: DifficultyEnum = Field(default=DifficultyEnum.EASY)
    category: str = Field(..., min_length=2, max_length=100)
    time_limit_ms: int = Field(default=2000, ge=100, le=10000)
    memory_limit_mb: int = Field(default=128, ge=16, le=512)
    sample_input: str = Field(default="")
    sample_output: str = Field(default="")
    boilerplate_code: Optional[Dict[str, str]] = Field(default=None)
    is_published: bool = Field(default=True)


class ProblemUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, min_length=10)
    difficulty: Optional[DifficultyEnum] = None
    category: Optional[str] = Field(None, min_length=2, max_length=100)
    time_limit_ms: Optional[int] = Field(None, ge=100, le=10000)
    memory_limit_mb: Optional[int] = Field(None, ge=16, le=512)
    sample_input: Optional[str] = None
    sample_output: Optional[str] = None
    boilerplate_code: Optional[Dict[str, str]] = None
    is_published: Optional[bool] = None


class ProblemResponse(BaseModel):
    id: str
    title: str
    slug: str
    difficulty: DifficultyEnum
    category: str
    time_limit_ms: int
    memory_limit_mb: int
    is_published: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProblemDetailResponse(ProblemResponse):
    description: str
    sample_input: str
    sample_output: str
    boilerplate_code: Optional[Dict[str, Any]] = None
    sample_test_cases: List[TestCasePublicResponse] = []


class ProblemAdminDetailResponse(ProblemDetailResponse):
    all_test_cases: List[TestCaseResponse] = []
