import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import SubmissionStatusEnum

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.problem import Problem
    from app.models.assessment import Assessment


class Submission(Base, TimestampMixin):
    __tablename__ = "submissions"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    candidate_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    problem_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("problems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assessment_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("assessments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    language: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[SubmissionStatusEnum] = mapped_column(
        Enum(SubmissionStatusEnum),
        default=SubmissionStatusEnum.QUEUED,
        nullable=False,
        index=True,
    )
    score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    max_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    execution_time_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    test_case_results: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )

    candidate: Mapped["User"] = relationship(
        "User",
        back_populates="submissions",
    )
    problem: Mapped["Problem"] = relationship(
        "Problem",
        back_populates="submissions",
    )
    assessment: Mapped[Optional["Assessment"]] = relationship(
        "Assessment",
        back_populates="submissions",
    )
