"""
Public NFC redirect logic.

This is the most security-sensitive module in the whole app: it decides
whether an anonymous customer tap gets forwarded to the entity's Google
Review page or shown an "unavailable" page. Nothing here may trust the
frontend, cached values, or a stale `status` column — every check reads
straight from the database and re-validates the subscription dates against
`datetime.now()` on every single request.
"""
import enum
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entity import Entity
from app.models.redirect_log import RedirectLog
from app.models.subscription import Subscription
from app.services.subscription_service import is_subscription_valid


class RedirectOutcome(str, enum.Enum):
    NOT_FOUND = "NOT_FOUND"          # no entity with this slug -> HTTP 404
    UNAVAILABLE = "UNAVAILABLE"      # inactive / no sub / expired / cancelled -> "unavailable" page
    VALID = "VALID"                  # -> HTTP 302 to google_review_url


@dataclass
class RedirectResult:
    outcome: RedirectOutcome
    entity: Optional[Entity] = None
    google_review_url: Optional[str] = None


def _get_latest_subscription(db: Session, entity_id: uuid.UUID) -> Optional[Subscription]:
    stmt = (
        select(Subscription)
        .where(Subscription.entity_id == entity_id)
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    return db.scalar(stmt)


def evaluate_redirect(db: Session, slug: str) -> RedirectResult:
    """
    Pure decision function (no side effects / no logging) — determines what
    should happen for a tap on this slug, reading fresh data from the DB.
    """
    entity = db.scalar(select(Entity).where(Entity.slug == slug))
    if entity is None:
        return RedirectResult(outcome=RedirectOutcome.NOT_FOUND)

    if not entity.is_active:
        return RedirectResult(outcome=RedirectOutcome.UNAVAILABLE, entity=entity)

    subscription = _get_latest_subscription(db, entity.id)
    if subscription is None:
        return RedirectResult(outcome=RedirectOutcome.UNAVAILABLE, entity=entity)

    # The critical re-check: status AND live date-range validity, evaluated
    # against the current moment — never trust a cached/stale status value.
    if not is_subscription_valid(subscription, now=datetime.now(timezone.utc)):
        return RedirectResult(outcome=RedirectOutcome.UNAVAILABLE, entity=entity)

    return RedirectResult(
        outcome=RedirectOutcome.VALID,
        entity=entity,
        google_review_url=entity.google_review_url,
    )


def log_redirect(
    db: Session,
    entity_id: uuid.UUID,
    user_agent: Optional[str],
    ip_address: Optional[str],
) -> None:
    """Records a successful redirect. Only called for RedirectOutcome.VALID."""
    log = RedirectLog(
        entity_id=entity_id,
        user_agent=(user_agent[:500] if user_agent else None),
        ip_address=(ip_address[:45] if ip_address else None),
    )
    db.add(log)
    db.commit()