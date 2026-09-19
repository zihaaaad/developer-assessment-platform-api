from dataclasses import dataclass
from typing import Optional
from app.models.enums import SubmissionStatusEnum


@dataclass
class ExecutionResult:
    status: SubmissionStatusEnum
    stdout: str
    stderr: str
    execution_time_ms: int
    error_message: Optional[str] = None
