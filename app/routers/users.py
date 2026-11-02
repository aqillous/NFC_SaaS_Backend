"""Platform-admin endpoints for managing user accounts."""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password
from app.dependencies.auth import get_current_superuser
from app.models.entity import Entity
from app.models.user import User
from app.schemas.auth import (
    PasswordReset,
    UserAdminCreate,
    UserAdminOut,
    UserStatusUpdate,
)

router = APIRouter(
    prefix="/api/users",
    tags=["users"],
    dependencies=[Depends(get_current_superuser)],
)


def _user_admin_data(user: User, entity_name: str | None) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "entity_id": user.entity_id,
        "created_at": user.created_at,
        "entity_name": entity_name,
    }


def _get_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


def _user_entity_name(db: Session, user: User) -> str | None:
    if user.entity_id is None:
        return None
    entity = db.get(Entity, user.entity_id)
    return entity.name if entity is not None else None


@router.get("", response_model=List[UserAdminOut])
def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(User, Entity.name)
        .outerjoin(Entity, User.entity_id == Entity.id)
        .order_by(User.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return [
        _user_admin_data(user, entity_name)
        for user, entity_name in rows
    ]


@router.post(
    "",
    response_model=UserAdminOut,
    status_code=status.HTTP_201_CREATED,
)
def create_user(
    payload: UserAdminCreate,
    db: Session = Depends(get_db),
):
    if payload.is_superuser and payload.entity_id is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Platform admins cannot be assigned to an entity",
        )
    if not payload.is_superuser and payload.entity_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Entity users must be assigned to an entity",
        )

    entity_name = None
    if payload.entity_id is not None:
        entity = db.get(Entity, payload.entity_id)
        if entity is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Entity not found",
            )
        entity_name = entity.name

    email = str(payload.email).lower()
    if db.query(User).filter(User.email == email).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        is_active=True,
        is_superuser=payload.is_superuser,
        entity_id=payload.entity_id,
    )
    db.add(user)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    db.refresh(user)
    return _user_admin_data(user, entity_name)


@router.post(
    "/{user_id}/reset-password",
    response_model=UserAdminOut,
)
def reset_user_password(
    user_id: uuid.UUID,
    payload: PasswordReset,
    db: Session = Depends(get_db),
):
    user = _get_user_or_404(db, user_id)
    user.password_hash = hash_password(payload.password)
    db.commit()
    db.refresh(user)
    return _user_admin_data(user, _user_entity_name(db, user))


@router.patch(
    "/{user_id}",
    response_model=UserAdminOut,
)
def update_user_status(
    user_id: uuid.UUID,
    payload: UserStatusUpdate,
    db: Session = Depends(get_db),
):
    user = _get_user_or_404(db, user_id)
    user.is_active = payload.is_active
    db.commit()
    db.refresh(user)
    return _user_admin_data(user, _user_entity_name(db, user))
