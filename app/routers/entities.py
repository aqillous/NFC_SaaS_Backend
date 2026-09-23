"""
Entity endpoints (admin-only).

Entity management is restricted to superusers.

This router also contains the endpoint used to create login accounts
for restaurants/hotels.
"""

import uuid
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password
from app.dependencies.auth import get_current_superuser
from app.models.entity import EntityType
from app.models.user import User
from app.schemas.auth import (
    EntityUserCreate,
    UserOut,
)
from app.schemas.entity import (
    EntityCreate,
    EntityOut,
    EntityUpdate,
)
from app.services import entity_service


router = APIRouter(
    prefix="/api/entities",
    tags=["entities"],
    dependencies=[
        Depends(get_current_superuser)
    ],
)


@router.get(
    "",
    response_model=List[EntityOut],
)
def list_entities(
    type: Optional[EntityType] = Query(
        None,
        description="Filter by RESTAURANT or HOTEL",
    ),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(
        None,
        description=(
            "Case-insensitive search on entity name"
        ),
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(
        100,
        ge=1,
        le=500,
    ),
    db: Session = Depends(get_db),
):
    return entity_service.list_entities(
        db,
        entity_type=type,
        is_active=is_active,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.post(
    "",
    response_model=EntityOut,
    status_code=status.HTTP_201_CREATED,
)
def create_entity(
    payload: EntityCreate,
    db: Session = Depends(get_db),
):
    return entity_service.create_entity(
        db,
        payload,
    )


@router.get(
    "/{entity_id}",
    response_model=EntityOut,
)
def get_entity(
    entity_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    return entity_service.get_entity(
        db,
        entity_id,
    )


@router.put(
    "/{entity_id}",
    response_model=EntityOut,
)
def update_entity(
    entity_id: uuid.UUID,
    payload: EntityUpdate,
    db: Session = Depends(get_db),
):
    return entity_service.update_entity(
        db,
        entity_id,
        payload,
    )


@router.delete(
    "/{entity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_entity(
    entity_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    entity_service.delete_entity(
        db,
        entity_id,
    )

    return None


# --------------------------------------------------------------------------
# ENTITY LOGIN CREATION
# --------------------------------------------------------------------------

@router.post(
    "/{entity_id}/users",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
)
def create_entity_user(
    entity_id: uuid.UUID,
    payload: EntityUserCreate,
    db: Session = Depends(get_db),
):
    """
    Create a login account for a restaurant/hotel.

    Only superusers can access this endpoint.

    The created user:
    - belongs to the selected entity
    - is not a superuser
    - is active by default
    - uses an Argon2 password hash
    """

    # Verify that the entity exists.
    entity = entity_service.get_entity_or_404(
        db,
        entity_id,
    )

    # Normalize email.
    email = payload.email.lower()

    # Check for an existing account.
    existing_user = (
        db.query(User)
        .filter(
            User.email == email
        )
        .first()
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A user with this email "
                "already exists"
            ),
        )

    user = User(
        email=email,
        password_hash=hash_password(
            payload.password
        ),
        is_active=True,
        is_superuser=False,
        entity_id=entity.id,
    )

    db.add(user)

    try:
        db.commit()

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A user with this email "
                "already exists"
            ),
        )

    db.refresh(user)

    return user