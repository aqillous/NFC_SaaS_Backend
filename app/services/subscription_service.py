"""
Subscription business logic. Routers stay thin and delegate everything here.

The single most important function in this module is `is_subscription_valid`,
which is the ONLY function allowed to decide whether a customer-facing
redirect should be permitted. It is deliberately duplicated-in-spirit by the
redirect_service (Phase 4), which re-derives validity from a *fresh* DB read
rather than trusting a cached value — see redirect_service.py for why.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional, Sequence

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entity import Entity
from app.models.subscription import Subscription, SubscriptionStatus
from app.schemas.subscription import (
    SubscriptionCreate,
    SubscriptionOut,
    SubscriptionUpdate,
)


def is_subscription_valid(sub: Subscription, now: Optional[datetime] = None) -> bool:
    """
    The canonical validity rule, used everywhere a decision is made:

        status == ACTIVE
        AND starts_at <= now <= ends_at

    `status` alone is NEVER sufficient — dates are always re-checked against
    the current wall-clock time, even if a background job to auto-expire
    subscriptions exists (it doesn't yet in this MVP; see Phase 4 notes).
    """
    now = now or datetime.now(timezone.utc)
    if sub.status != SubscriptionStatus.ACTIVE:
        return False
    starts_at = sub.starts_at if sub.starts_at.tzinfo else sub.starts_at.replace(tzinfo=timezone.utc)
    ends_at = sub.ends_at if sub.ends_at.tzinfo else sub.ends_at.replace(tzinfo=timezone.utc)
    return starts_at <= now <= ends_at


def _to_out(sub: Subscription) -> SubscriptionOut:
    return SubscriptionOut(
        id=sub.id,
        entity_id=sub.entity_id,
        starts_at=sub.starts_at,
        ends_at=sub.ends_at,
        status=sub.status,
        created_at=sub.created_at,
        updated_at=sub.updated_at,
        is_currently_valid=is_subscription_valid(sub),
    )


def _get_entity_or_404(db: Session, entity_id: uuid.UUID) -> Entity:
    entity = db.get(Entity, entity_id)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    return entity


def get_subscription_or_404(db: Session, subscription_id: uuid.UUID) -> Subscription:
    sub = db.get(Subscription, subscription_id)
    if sub is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    return sub


def get_subscription(db: Session, subscription_id: uuid.UUID) -> SubscriptionOut:
    return _to_out(get_subscription_or_404(db, subscription_id))


def create_subscription(db: Session, payload: SubscriptionCreate) -> SubscriptionOut:
    # Fail fast with a clean 404 if the entity doesn't exist, rather than
    # letting the FK constraint raise an opaque IntegrityError.
    _get_entity_or_404(db, payload.entity_id)

    sub = Subscription(
        entity_id=payload.entity_id,
        starts_at=payload.starts_at,
        ends_at=payload.ends_at,
        status=payload.status,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return _to_out(sub)


def list_subscriptions(
    db: Session,
    entity_id: Optional[uuid.UUID] = None,
    status_filter: Optional[SubscriptionStatus] = None,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[SubscriptionOut]:
    stmt = select(Subscription)
    if entity_id is not None:
        stmt = stmt.where(Subscription.entity_id == entity_id)
    if status_filter is not None:
        stmt = stmt.where(Subscription.status == status_filter)
    stmt = stmt.order_by(Subscription.created_at.desc()).offset(skip).limit(limit)

    subs = db.scalars(stmt).all()
    return [_to_out(s) for s in subs]


def update_subscription(
    db: Session, subscription_id: uuid.UUID, payload: SubscriptionUpdate
) -> SubscriptionOut:
    sub = get_subscription_or_404(db, subscription_id)

    update_data = payload.model_dump(exclude_unset=True)

    # Validate the *resulting* date pair, since PUT may only send one of the two.
    new_starts_at = update_data.get("starts_at", sub.starts_at)
    new_ends_at = update_data.get("ends_at", sub.ends_at)
    if new_ends_at <= new_starts_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ends_at must be after starts_at",
        )

    for field, value in update_data.items():
        setattr(sub, field, value)

    db.add(sub)
    db.commit()
    db.refresh(sub)
    return _to_out(sub)


def delete_subscription(db: Session, subscription_id: uuid.UUID) -> None:
    sub = get_subscription_or_404(db, subscription_id)
    db.delete(sub)
    db.commit()


def get_current_subscription_for_entity(db: Session, entity_id: uuid.UUID) -> Optional[Subscription]:
    """
    The subscription an admin would consider "current" for an entity: the
    most recently created one. Used by the dashboard / entity detail view.
    (The redirect endpoint in Phase 4 does its own lookup — see there.)
    """
    stmt = (
        select(Subscription)
        .where(Subscription.entity_id == entity_id)
        .order_by(Subscription.created_at.desc())
        .limit(1)
    )
    return db.scalar(stmt)