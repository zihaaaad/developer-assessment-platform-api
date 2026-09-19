from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import AssessmentStatusEnum
from app.schemas.problem import ProblemResponse


class AssessmentProblemAdd(BaseModel):
    problem_id: str
    order_index: int = Field(default=0, ge=0)
    points: int = Field(default=100, ge=1, le=1000)


class AssessmentProblemResponse(BaseModel):
    problem_id: str
    order_index: int
    points: int
    problem: ProblemResponse

    model_config = ConfigDict(from_attributes=True)


class AssessmentCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=200)
    description: str = Field(..., min_length=10)
    start_time: datetime
    end_time: datetime
    duration_minutes: int = Field(..., ge=5, le=1440)
    passing_score: int = Field(default=50, ge=0, le=1000)
    status: AssessmentStatusEnum = Field(default=AssessmentStatusEnum.DRAFT)
    problems: Optional[List[AssessmentProblemAdd]] = None


class AssessmentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, min_length=10)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_minutes: Optional[int] = Field(None, ge=5, le=1440)
    passing_score: Optional[int] = Field(None, ge=0, le=1000)
    status: Optional[AssessmentStatusEnum] = None


class AssessmentResponse(BaseModel):
    id: str
    recruiter_id: str
    title: str
    description: str
    start_time: datetime
    end_time: datetime
    duration_minutes: int
    passing_score: int
    status: AssessmentStatusEnum
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssessmentDetailResponse(AssessmentResponse):
    problems: List[AssessmentProblemResponse] = []
