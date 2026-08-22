"""
Entity model — a restaurant or hotel using the service.

The `slug` is the permanent, randomly-generated identifier embedded in the
NFC card URL (https://mydomain.com/r/{slug}). It is NEVER regenerated once
created, even if the entity's name or Google Review URL changes later.
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime
from sqlalchemy import Enum as SAEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.types import GUID


class EntityType(str, enum.Enum):
    RESTAURANT = "RESTAURANT"
    HOTEL = "HOTEL"


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[EntityType] = mapped_column(SAEnum(EntityType, name="entity_type"), nullable=False)
    google_review_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    slug: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # NOTE: `subscriptions` and `redirect_logs` relationships are added in
    # Phase 3 / Phase 4, once those models exist.

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Entity id={self.id} name={self.name!r} slug={self.slug}>"