import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import AssessmentStatusEnum

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.problem import Problem
    from app.models.submission import Submission
    from app.models.assessment_result import AssessmentResult


class AssessmentProblem(Base):
    __tablename__ = "assessment_problems"

    assessment_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        primary_key=True,
    )
    problem_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("problems.id", ondelete="CASCADE"),
        primary_key=True,
    )
    order_index: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    points: Mapped[int] = mapped_column(
        Integer,
        default=100,
        nullable=False,
    )

    assessment: Mapped["Assessment"] = relationship(
        "Assessment",
        back_populates="problems",
    )
    problem: Mapped["Problem"] = relationship(
        "Problem",
        back_populates="assessment_links",
    )


class Assessment(Base, TimestampMixin):
    __tablename__ = "assessments"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    recruiter_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    end_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    passing_score: Mapped[int] = mapped_column(
        Integer,
        default=50,
        nullable=False,
    )
    status: Mapped[AssessmentStatusEnum] = mapped_column(
        Enum(AssessmentStatusEnum),
        default=AssessmentStatusEnum.DRAFT,
        nullable=False,
        index=True,
    )

    recruiter: Mapped["User"] = relationship(
        "User",
        back_populates="created_assessments",
    )
    problems: Mapped[List[AssessmentProblem]] = relationship(
        "AssessmentProblem",
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="AssessmentProblem.order_index",
    )
    submissions: Mapped[List["Submission"]] = relationship(
        "Submission",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )
    results: Mapped[List["AssessmentResult"]] = relationship(
        "AssessmentResult",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )
