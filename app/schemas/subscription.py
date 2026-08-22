import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.subscription import SubscriptionStatus


class SubscriptionBase(BaseModel):
    entity_id: uuid.UUID
    starts_at: datetime
    ends_at: datetime
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE

    @model_validator(mode="after")
    def check_date_order(self) -> "SubscriptionBase":
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        return self


class SubscriptionCreate(SubscriptionBase):
    pass


class SubscriptionUpdate(BaseModel):
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    status: Optional[SubscriptionStatus] = None

    @model_validator(mode="after")
    def check_date_order(self) -> "SubscriptionUpdate":
        if self.starts_at is not None and self.ends_at is not None:
            if self.ends_at <= self.starts_at:
                raise ValueError("ends_at must be after starts_at")
        return self


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    entity_id: uuid.UUID
    starts_at: datetime
    ends_at: datetime
    status: SubscriptionStatus
    created_at: datetime
    updated_at: datetime
    # Convenience field for the admin UI: whether this subscription would
    # currently pass the redirect endpoint's live validity check.
    is_currently_valid: bool = Field(
        description="True if status == ACTIVE and now is within [starts_at, ends_at]"
    )


# Nested inside EntityOut when we want to show an entity's current subscription
# without a second API call (used by the "create entity" response, dashboard, etc.)
class SubscriptionNested(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    starts_at: datetime
    ends_at: datetime
    status: SubscriptionStatus
    is_currently_valid: bool