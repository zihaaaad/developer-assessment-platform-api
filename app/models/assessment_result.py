import uuid
from typing import TYPE_CHECKING, Optional
from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.assessment import Assessment


class AssessmentResult(Base, TimestampMixin):
    __tablename__ = "assessment_results"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    assessment_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    candidate_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    total_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    problems_solved: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    total_time_seconds: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    rank: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )

    assessment: Mapped["Assessment"] = relationship(
        "Assessment",
        back_populates="results",
    )
    candidate: Mapped["User"] = relationship(
        "User",
        back_populates="assessment_results",
    )

    __table_args__ = (
        UniqueConstraint("assessment_id", "candidate_id", name="uq_assessment_candidate"),
    )
