import uuid
from typing import TYPE_CHECKING
from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.problem import Problem


class TestCase(Base, TimestampMixin):
    __tablename__ = "test_cases"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    problem_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("problems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    input_data: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    expected_output: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    is_hidden: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    score_weight: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False,
    )

    problem: Mapped["Problem"] = relationship(
        "Problem",
        back_populates="test_cases",
    )
