"""
Subscription endpoints (admin-only).

Every route in this router requires a valid admin JWT — enforced via the
`dependencies=[Depends(get_current_user)]` on the router itself.
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.subscription import SubscriptionStatus
from app.schemas.subscription import SubscriptionCreate, SubscriptionOut, SubscriptionUpdate
from app.services import subscription_service

router = APIRouter(
    prefix="/api/subscriptions",
    tags=["subscriptions"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=List[SubscriptionOut])
def list_subscriptions(
    entity_id: Optional[uuid.UUID] = Query(None),
    status_filter: Optional[SubscriptionStatus] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return subscription_service.list_subscriptions(
        db, entity_id=entity_id, status_filter=status_filter, skip=skip, limit=limit
    )


@router.post("", response_model=SubscriptionOut, status_code=status.HTTP_201_CREATED)
def create_subscription(payload: SubscriptionCreate, db: Session = Depends(get_db)):
    return subscription_service.create_subscription(db, payload)


@router.get("/{subscription_id}", response_model=SubscriptionOut)
def get_subscription(subscription_id: uuid.UUID, db: Session = Depends(get_db)):
    return subscription_service.get_subscription(db, subscription_id)


@router.put("/{subscription_id}", response_model=SubscriptionOut)
def update_subscription(
    subscription_id: uuid.UUID, payload: SubscriptionUpdate, db: Session = Depends(get_db)
):
    return subscription_service.update_subscription(db, subscription_id, payload)


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(subscription_id: uuid.UUID, db: Session = Depends(get_db)):
    subscription_service.delete_subscription(db, subscription_id)
    return None