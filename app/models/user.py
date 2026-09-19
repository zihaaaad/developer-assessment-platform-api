import uuid
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin
from app.models.enums import RoleEnum

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.submission import Submission
    from app.models.assessment_result import AssessmentResult


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[RoleEnum] = mapped_column(
        Enum(RoleEnum),
        default=RoleEnum.CANDIDATE,
        nullable=False,
    )
    refresh_token: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
    )
    password_reset_token: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    password_reset_expires: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_assessments: Mapped[List["Assessment"]] = relationship(
        "Assessment",
        back_populates="recruiter",
        cascade="all, delete-orphan",
    )
    submissions: Mapped[List["Submission"]] = relationship(
        "Submission",
        back_populates="candidate",
        cascade="all, delete-orphan",
    )
    assessment_results: Mapped[List["AssessmentResult"]] = relationship(
        "AssessmentResult",
        back_populates="candidate",
        cascade="all, delete-orphan",
    )
