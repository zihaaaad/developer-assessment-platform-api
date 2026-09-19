import uuid
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, Enum, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import DifficultyEnum

if TYPE_CHECKING:
    from app.models.test_case import TestCase
    from app.models.submission import Submission
    from app.models.assessment import AssessmentProblem


class Problem(Base, TimestampMixin):
    __tablename__ = "problems"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )
    slug: Mapped[str] = mapped_column(
        String(220),
        unique=True,
        index=True,
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    difficulty: Mapped[DifficultyEnum] = mapped_column(
        Enum(DifficultyEnum),
        default=DifficultyEnum.EASY,
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    time_limit_ms: Mapped[int] = mapped_column(
        Integer,
        default=2000,
        nullable=False,
    )
    memory_limit_mb: Mapped[int] = mapped_column(
        Integer,
        default=128,
        nullable=False,
    )
    sample_input: Mapped[str] = mapped_column(
        Text,
        default="",
        nullable=False,
    )
    sample_output: Mapped[str] = mapped_column(
        Text,
        default="",
        nullable=False,
    )
    boilerplate_code: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
    )
    is_published: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    test_cases: Mapped[List["TestCase"]] = relationship(
        "TestCase",
        back_populates="problem",
        cascade="all, delete-orphan",
    )
    submissions: Mapped[List["Submission"]] = relationship(
        "Submission",
        back_populates="problem",
        cascade="all, delete-orphan",
    )
    assessment_links: Mapped[List["AssessmentProblem"]] = relationship(
        "AssessmentProblem",
        back_populates="problem",
        cascade="all, delete-orphan",
    )
