from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import LanguageEnum, SubmissionStatusEnum


class SubmissionCreate(BaseModel):
    problem_id: str
    assessment_id: Optional[str] = None
    language: LanguageEnum
    code: str = Field(..., min_length=1, max_length=65536, description="Source code text (max 64KB)")


class RunSampleCodeRequest(BaseModel):
    problem_id: str
    language: LanguageEnum
    code: str = Field(..., min_length=1, max_length=65536)
    custom_input: Optional[str] = None


class SampleExecutionResult(BaseModel):
    status: SubmissionStatusEnum
    stdout: str
    stderr: str
    execution_time_ms: int
    expected_output: Optional[str] = None
    passed: bool = False
    error_message: Optional[str] = None


class TestCaseRunResult(BaseModel):
    test_case_id: str
    is_hidden: bool
    passed: bool
    execution_time_ms: int
    score_awarded: int
    max_score: int
    stdout: Optional[str] = None
    expected_output: Optional[str] = None
    error_message: Optional[str] = None


class SubmissionResponse(BaseModel):
    id: str
    candidate_id: str
    problem_id: str
    assessment_id: Optional[str]
    language: str
    status: SubmissionStatusEnum
    score: int
    max_score: int
    execution_time_ms: Optional[int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SubmissionDetailResponse(SubmissionResponse):
    code: str
    error_message: Optional[str] = None
    test_case_results: Optional[List[TestCaseRunResult]] = None
