"""
Dashboard business logic. Aggregates counts for the admin overview page.

Nothing here is security-sensitive (it's admin-only, read-only, aggregate
data), but it still reuses `is_subscription_valid` as the single source of
truth for "is this subscription currently valid" rather than re-deriving
the rule here.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.entity import Entity, EntityType
from app.models.redirect_log import RedirectLog
from app.models.subscription import Subscription, SubscriptionStatus
from app.schemas.dashboard import DashboardStats
from app.services.subscription_service import is_subscription_valid

EXPIRING_SOON_WINDOW_DAYS = 7


def get_dashboard_stats(db: Session) -> DashboardStats:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today_start.replace(day=1)
    expiring_soon_cutoff = now + timedelta(days=EXPIRING_SOON_WINDOW_DAYS)

    total_entities = db.scalar(select(func.count()).select_from(Entity)) or 0
    total_restaurants = db.scalar(
        select(func.count()).select_from(Entity).where(Entity.type == EntityType.RESTAURANT)
    ) or 0
    total_hotels = db.scalar(
        select(func.count()).select_from(Entity).where(Entity.type == EntityType.HOTEL)
    ) or 0

    # Pull minimal columns for every subscription and evaluate validity in
    # Python via the canonical `is_subscription_valid` — avoids duplicating
    # the date-comparison rule as raw SQL in a second place.
    subs = db.scalars(select(Subscription)).all()

    active_subscriptions = 0
    expired_subscriptions = 0
    expiring_soon = 0
    for sub in subs:
        valid = is_subscription_valid(sub, now=now)
        if valid:
            active_subscriptions += 1
            ends_at = sub.ends_at if sub.ends_at.tzinfo else sub.ends_at.replace(tzinfo=timezone.utc)
            if ends_at <= expiring_soon_cutoff:
                expiring_soon += 1
        elif sub.status in (SubscriptionStatus.EXPIRED, SubscriptionStatus.CANCELLED) or (
            sub.status == SubscriptionStatus.ACTIVE
        ):
            # Anything not currently valid (including a stale ACTIVE row
            # whose dates have lapsed) counts as expired for this tile.
            expired_subscriptions += 1

    scans_today = db.scalar(
        select(func.count()).select_from(RedirectLog).where(RedirectLog.created_at >= today_start)
    ) or 0
    scans_this_month = db.scalar(
        select(func.count()).select_from(RedirectLog).where(RedirectLog.created_at >= month_start)
    ) or 0

    return DashboardStats(
        total_entities=total_entities,
        total_restaurants=total_restaurants,
        total_hotels=total_hotels,
        active_subscriptions=active_subscriptions,
        expired_subscriptions=expired_subscriptions,
        expiring_soon=expiring_soon,
        scans_today=scans_today,
        scans_this_month=scans_this_month,
    )
