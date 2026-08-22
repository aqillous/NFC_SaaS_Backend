"""
Subscription model — represents a paid access period for an Entity.

Subscriptions are managed entirely by administrators (create/update/delete).
There is no self-service or payment flow. The `status` field records the
administrator's *intent*, but it must NEVER be trusted on its own to decide
whether a redirect is allowed: the redirect endpoint always re-checks
`starts_at <= now <= ends_at` in addition to `status == ACTIVE`. This
protects against a subscription whose dates have quietly expired while an
admin forgot (or a scheduled job hasn't yet run) to flip the status.
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.types import GUID


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    entity_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(
        SAEnum(SubscriptionStatus, name="subscription_status"),
        nullable=False,
        default=SubscriptionStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    entity = relationship("Entity", backref="subscriptions")

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<Subscription id={self.id} entity_id={self.entity_id} "
            f"status={self.status} ends_at={self.ends_at}>"
        )