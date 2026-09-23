"""
Customer feedback submitted on the NFC review landing page.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.types import GUID


class Feedback(Base):
    __tablename__ = "feedback"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        primary_key=True,
        default=uuid.uuid4,
    )

    entity_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    quality: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    service: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    taste: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    overall_score: Mapped[float] = mapped_column(
        nullable=False,
    )

    comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    redirected_to_google: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )

    user_agent: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )

    entity = relationship(
        "Entity",
        backref="feedback",
    )

    __table_args__ = (
        CheckConstraint(
            "quality BETWEEN 1 AND 5",
            name="ck_feedback_quality",
        ),
        CheckConstraint(
            "service BETWEEN 1 AND 5",
            name="ck_feedback_service",
        ),
        CheckConstraint(
            "taste BETWEEN 1 AND 5",
            name="ck_feedback_taste",
        ),
        CheckConstraint(
            "overall_score >= 1 AND overall_score <= 5",
            name="ck_feedback_overall",
        ),
        Index(
            "ix_feedback_entity_created_at",
            "entity_id",
            "created_at",
        ),
    )