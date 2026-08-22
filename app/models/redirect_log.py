"""
RedirectLog model — one row per successful NFC tap that resulted in a
redirect to Google. Used later for scan analytics (Phase 6).

We deliberately only log *successful* redirects here (not 404s, inactive
entities, or expired subscriptions) — that keeps this table meaningful as
"how many times was this card tapped by a real customer and sent to
Google", which is the number restaurants/hotels actually care about.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.types import GUID


class RedirectLog(Base):
    __tablename__ = "redirect_logs"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    entity_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("entities.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    entity = relationship("Entity", backref="redirect_logs")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RedirectLog id={self.id} entity_id={self.entity_id} created_at={self.created_at}>"