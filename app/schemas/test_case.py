from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class TestCaseCreate(BaseModel):
    input_data: str = Field(..., description="Standard input string or argument representation")
    expected_output: str = Field(..., description="Expected standard output string")
    is_hidden: bool = Field(default=True, description="Hidden test cases are used for grading and hidden from candidate previews")
    score_weight: int = Field(default=10, ge=1, le=100)


class TestCaseUpdate(BaseModel):
    input_data: Optional[str] = None
    expected_output: Optional[str] = None
    is_hidden: Optional[bool] = None
    score_weight: Optional[int] = Field(None, ge=1, le=100)


class TestCaseResponse(BaseModel):
    id: str
    problem_id: str
    input_data: str
    expected_output: str
    is_hidden: bool
    score_weight: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TestCasePublicResponse(BaseModel):
    id: str
    problem_id: str
    input_data: str
    expected_output: str
    score_weight: int

    model_config = ConfigDict(from_attributes=True)
