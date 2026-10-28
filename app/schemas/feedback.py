import uuid

from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

FEEDBACK_REASONS = {
    "service_speed",
    "staff_attitude",
    "product_quality",
}


class FeedbackSubmit(BaseModel):
    quality: int = Field(
        ...,
        ge=1,
        le=5,
    )

    service: int = Field(
        ...,
        ge=1,
        le=5,
    )

    taste: int = Field(
        ...,
        ge=1,
        le=5,
    )

    comment: Optional[str] = Field(
        None,
        max_length=2000,
    )

    reasons: list[str] = Field(
        default_factory=list,
        max_length=3,
    )

    redirected_to_google: bool = False

    @field_validator("comment")
    @classmethod
    def clean_comment(
        cls,
        value: Optional[str],
    ) -> Optional[str]:

        if value is None:
            return None

        value = value.strip()

        return value or None

    @field_validator("reasons")
    @classmethod
    def validate_reasons(cls, value: list[str]) -> list[str]:
        if (
            len(set(value)) != len(value)
            or not set(value).issubset(FEEDBACK_REASONS)
        ):
            raise ValueError("Invalid feedback reasons")
        return value


class FeedbackOut(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )

    id: uuid.UUID
    entity_id: uuid.UUID

    quality: int
    service: int
    taste: int

    overall_score: float

    comment: Optional[str]

    reasons: list[str] = Field(default_factory=list)

    redirected_to_google: bool

    created_at: datetime


class FeedbackStats(BaseModel):
    total_submissions: int

    average_score: float

    average_quality: float
    average_service: float
    average_taste: float

    google_redirects: int
    internal_feedback: int

    google_redirect_rate: float

    submissions_today: int
    submissions_this_month: int


class DailyFeedbackStat(BaseModel):
    date: str
    submissions: int
    average_score: float
    google_redirects: int


class RestaurantDashboard(BaseModel):
    entity_id: uuid.UUID

    entity_name: str

    stats: FeedbackStats

    daily: list[DailyFeedbackStat]