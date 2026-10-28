"""
Dashboard business logic. Aggregates counts for the admin overview page.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entity import Entity, EntityType
from app.models.redirect_log import RedirectLog
from app.models.feedback import Feedback
from app.models.subscription import Subscription, SubscriptionStatus
from app.schemas.dashboard import DashboardStats
from app.services.subscription_service import is_subscription_valid


EXPIRING_SOON_WINDOW_DAYS = 7


def get_dashboard_stats(db: Session) -> DashboardStats:
    now = datetime.now(timezone.utc)

    today_start = now.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    month_start = today_start.replace(day=1)

    expiring_soon_cutoff = now + timedelta(
        days=EXPIRING_SOON_WINDOW_DAYS
    )

    # ---------------------------------------------------------
    # ENTITIES
    # ---------------------------------------------------------

    total_entities = db.scalar(
        select(func.count()).select_from(Entity)
    ) or 0

    total_restaurants = db.scalar(
        select(func.count())
        .select_from(Entity)
        .where(Entity.type == EntityType.RESTAURANT)
    ) or 0

    total_hotels = db.scalar(
        select(func.count())
        .select_from(Entity)
        .where(Entity.type == EntityType.HOTEL)
    ) or 0

    # ---------------------------------------------------------
    # SUBSCRIPTIONS
    # ---------------------------------------------------------

    subs = db.scalars(
        select(Subscription)
    ).all()

    active_subscriptions = 0
    expired_subscriptions = 0
    expiring_soon = 0

    for sub in subs:
        valid = is_subscription_valid(
            sub,
            now=now,
        )

        if valid:
            active_subscriptions += 1

            ends_at = (
                sub.ends_at
                if sub.ends_at.tzinfo
                else sub.ends_at.replace(
                    tzinfo=timezone.utc
                )
            )

            if ends_at <= expiring_soon_cutoff:
                expiring_soon += 1

        elif (
            sub.status in (
                SubscriptionStatus.EXPIRED,
                SubscriptionStatus.CANCELLED,
            )
            or sub.status == SubscriptionStatus.ACTIVE
        ):
            expired_subscriptions += 1

    # ---------------------------------------------------------
    # SCANS
    # ---------------------------------------------------------

    scans_today = db.scalar(
        select(func.count())
        .select_from(RedirectLog)
        .where(
            RedirectLog.created_at >= today_start
        )
    ) or 0

    scans_this_month = db.scalar(
        select(func.count())
        .select_from(RedirectLog)
        .where(
            RedirectLog.created_at >= month_start
        )
    ) or 0

    scans_today += db.scalar(
        select(func.count())
        .select_from(Feedback)
        .where(
            Feedback.redirected_to_google.is_(True),
            Feedback.created_at >= today_start,
        )
    ) or 0

    scans_this_month += db.scalar(
        select(func.count())
        .select_from(Feedback)
        .where(
            Feedback.redirected_to_google.is_(True),
            Feedback.created_at >= month_start,
        )
    ) or 0

    # ---------------------------------------------------------
    # FEEDBACK
    # ---------------------------------------------------------

    total_feedback = db.scalar(
        select(func.count())
        .select_from(Feedback)
    ) or 0

    average_feedback_score = db.scalar(
        select(func.avg(Feedback.overall_score))
    ) or 0

    average_quality = db.scalar(
        select(func.avg(Feedback.quality))
    ) or 0

    average_service = db.scalar(
        select(func.avg(Feedback.service))
    ) or 0

    average_taste = db.scalar(
        select(func.avg(Feedback.taste))
    ) or 0

    feedback_google_redirects = db.scalar(
        select(func.count())
        .select_from(Feedback)
        .where(
            Feedback.redirected_to_google.is_(True)
        )
    ) or 0

    logged_google_redirects = db.scalar(
        select(func.count())
        .select_from(RedirectLog)
    ) or 0

    google_redirects = (
        feedback_google_redirects
        + logged_google_redirects
    )

    internal_feedback = (
        total_feedback - feedback_google_redirects
    )

    total_review_choices = google_redirects + internal_feedback
    google_redirect_rate = (
        (google_redirects / total_review_choices) * 100
        if total_review_choices > 0
        else 0
    )

    feedback_today = db.scalar(
        select(func.count())
        .select_from(Feedback)
        .where(
            Feedback.created_at >= today_start
        )
    ) or 0

    feedback_this_month = db.scalar(
        select(func.count())
        .select_from(Feedback)
        .where(
            Feedback.created_at >= month_start
        )
    ) or 0

    # ---------------------------------------------------------
    # RESULT
    # ---------------------------------------------------------

    return DashboardStats(
        total_entities=total_entities,
        total_restaurants=total_restaurants,
        total_hotels=total_hotels,

        active_subscriptions=active_subscriptions,
        expired_subscriptions=expired_subscriptions,
        expiring_soon=expiring_soon,

        scans_today=scans_today,
        scans_this_month=scans_this_month,

        total_feedback=total_feedback,
        average_feedback_score=round(
            float(average_feedback_score),
            2,
        ),

        average_quality=round(
            float(average_quality),
            2,
        ),

        average_service=round(
            float(average_service),
            2,
        ),

        average_taste=round(
            float(average_taste),
            2,
        ),

        google_redirects=google_redirects,
        internal_feedback=internal_feedback,

        google_redirect_rate=round(
            float(google_redirect_rate),
            2,
        ),

        feedback_today=feedback_today,
        feedback_this_month=feedback_this_month,
    )