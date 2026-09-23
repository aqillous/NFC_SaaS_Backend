"""
Feedback business logic.
"""

import uuid

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from typing import Optional

from sqlalchemy import (
    case,
    func,
    select,
)

from sqlalchemy.orm import Session

from app.models.entity import Entity
from app.models.feedback import Feedback

from app.schemas.feedback import (
    DailyFeedbackStat,
    FeedbackOut,
    FeedbackStats,
    RestaurantDashboard,
)


# Customer needs MORE than 4.0 to be redirected.
GOOGLE_REDIRECT_THRESHOLD = 4.0


def calculate_overall_score(
    quality: int,
    service: int,
    taste: int,
) -> float:

    return round(
        (quality + service + taste) / 3,
        2,
    )


def create_feedback(
    db: Session,
    entity: Entity,
    quality: int,
    service: int,
    taste: int,
    comment: Optional[str],
    user_agent: Optional[str],
    ip_address: Optional[str],
) -> tuple[FeedbackOut, bool]:

    overall = calculate_overall_score(
        quality,
        service,
        taste,
    )

    should_redirect = (
        overall > GOOGLE_REDIRECT_THRESHOLD
    )

    feedback = Feedback(
        entity_id=entity.id,

        quality=quality,
        service=service,
        taste=taste,

        overall_score=overall,

        comment=comment,

        redirected_to_google=should_redirect,

        user_agent=(
            user_agent[:500]
            if user_agent
            else None
        ),

        ip_address=(
            ip_address[:45]
            if ip_address
            else None
        ),
    )

    db.add(feedback)

    db.commit()

    db.refresh(feedback)

    return FeedbackOut.model_validate(feedback), should_redirect


def _empty_stats() -> FeedbackStats:

    return FeedbackStats(
        total_submissions=0,

        average_score=0,

        average_quality=0,
        average_service=0,
        average_taste=0,

        google_redirects=0,
        internal_feedback=0,

        google_redirect_rate=0,

        submissions_today=0,
        submissions_this_month=0,
    )


def get_stats(
    db: Session,
    entity_id: uuid.UUID,
) -> FeedbackStats:

    now = datetime.now(timezone.utc)

    today_start = now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    month_start = today_start.replace(
        day=1
    )

    row = db.execute(
        select(
            func.count(
                Feedback.id
            ).label("total"),

            func.avg(
                Feedback.overall_score
            ).label("avg_score"),

            func.avg(
                Feedback.quality
            ).label("avg_quality"),

            func.avg(
                Feedback.service
            ).label("avg_service"),

            func.avg(
                Feedback.taste
            ).label("avg_taste"),

            func.sum(
                case(
                    (
                        Feedback.redirected_to_google.is_(True),
                        1,
                    ),
                    else_=0,
                )
            ).label("redirects"),

            func.sum(
                case(
                    (
                        Feedback.created_at >= today_start,
                        1,
                    ),
                    else_=0,
                )
            ).label("today"),

            func.sum(
                case(
                    (
                        Feedback.created_at >= month_start,
                        1,
                    ),
                    else_=0,
                )
            ).label("month"),
        )
        .where(
            Feedback.entity_id == entity_id
        )
    ).one()

    total = int(
        row.total or 0
    )

    redirects = int(
        row.redirects or 0
    )

    if total == 0:
        return _empty_stats()

    return FeedbackStats(
        total_submissions=total,

        average_score=round(
            float(row.avg_score or 0),
            2,
        ),

        average_quality=round(
            float(row.avg_quality or 0),
            2,
        ),

        average_service=round(
            float(row.avg_service or 0),
            2,
        ),

        average_taste=round(
            float(row.avg_taste or 0),
            2,
        ),

        google_redirects=redirects,

        internal_feedback=(
            total - redirects
        ),

        google_redirect_rate=round(
            (redirects / total) * 100,
            2,
        ),

        submissions_today=int(
            row.today or 0
        ),

        submissions_this_month=int(
            row.month or 0
        ),
    )


def get_dashboard(
    db: Session,
    entity: Entity,
    days: int = 30,
) -> RestaurantDashboard:

    days = max(
        1,
        min(days, 365),
    )

    now = datetime.now(timezone.utc)

    start = (
        now
        - timedelta(days=days - 1)
    ).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    daily_rows = db.execute(
        select(
            func.date(
                Feedback.created_at
            ).label("day"),

            func.count(
                Feedback.id
            ).label("submissions"),

            func.avg(
                Feedback.overall_score
            ).label("average_score"),

            func.sum(
                case(
                    (
                        Feedback.redirected_to_google.is_(True),
                        1,
                    ),
                    else_=0,
                )
            ).label("google_redirects"),
        )
        .where(
            Feedback.entity_id == entity.id,
            Feedback.created_at >= start,
        )
        .group_by(
            func.date(
                Feedback.created_at
            )
        )
        .order_by(
            func.date(
                Feedback.created_at
            )
        )
    ).all()

    daily = [
        DailyFeedbackStat(
            date=str(row.day),

            submissions=int(
                row.submissions
            ),

            average_score=round(
                float(
                    row.average_score or 0
                ),
                2,
            ),

            google_redirects=int(
                row.google_redirects or 0
            ),
        )

        for row in daily_rows
    ]

    return RestaurantDashboard(
        entity_id=entity.id,

        entity_name=entity.name,

        stats=get_stats(
            db,
            entity.id,
        ),

        daily=daily,
    )


def list_feedback(
    db: Session,
    entity_id: uuid.UUID,
    skip: int = 0,
    limit: int = 50,
) -> list[FeedbackOut]:

    rows = db.scalars(
        select(Feedback)
        .where(
            Feedback.entity_id == entity_id
        )
        .order_by(
            Feedback.created_at.desc()
        )
        .offset(skip)
        .limit(limit)
    ).all()

    return [
        FeedbackOut.model_validate(row)
        for row in rows
    ]