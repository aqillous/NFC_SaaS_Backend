import uuid
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.entity import EntityType

# Domains (and subdomains of them) we accept as valid Google review links.
# Covers the common real-world formats:
#   https://g.page/r/xxxxxxxxxxxx/review
#   https://search.google.com/local/writereview?placeid=xxxx
#   https://maps.google.com/?cid=xxxx
#   https://maps.app.goo.gl/xxxx
_ALLOWED_GOOGLE_REVIEW_DOMAINS = ("google.com", "goo.gl", "g.page")


def _is_valid_google_review_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.netloc or "").lower()
    if not host:
        return False
    return any(host == d or host.endswith("." + d) for d in _ALLOWED_GOOGLE_REVIEW_DOMAINS)


class EntityBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    type: EntityType
    google_review_url: str = Field(..., max_length=1000)

    @field_validator("google_review_url")
    @classmethod
    def validate_google_review_url(cls, v: str) -> str:
        if not _is_valid_google_review_url(v):
            raise ValueError(
                "google_review_url must be a valid Google link "
                "(e.g. https://g.page/r/.../review, "
                "https://search.google.com/local/writereview?placeid=..., "
                "or https://maps.app.goo.gl/...)"
            )
        return v


class EntityCreate(EntityBase):
    """Fields accepted when creating a new entity. Slug is generated server-side."""
    pass


class EntityUpdate(BaseModel):
    """
    Fields an admin can change. Notably absent: `slug`. There is no way to
    submit a slug change through this schema — the NFC URL is permanent.
    """
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    type: Optional[EntityType] = None
    google_review_url: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None

    @field_validator("google_review_url")
    @classmethod
    def validate_google_review_url(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not _is_valid_google_review_url(v):
            raise ValueError(
                "google_review_url must be a valid Google link "
                "(e.g. https://g.page/r/.../review)"
            )
        return v


class EntityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    type: EntityType
    google_review_url: str
    slug: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    nfc_url: str  # computed: PUBLIC_BASE_URL + /r/{slug}