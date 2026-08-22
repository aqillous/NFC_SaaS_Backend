"""
Entity endpoints (admin-only).

Every route in this router requires a valid admin JWT — enforced via the
`dependencies=[Depends(get_current_user)]` on the router itself, so it's
impossible to accidentally add a new route here that forgets auth.
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.models.entity import EntityType
from app.schemas.entity import EntityCreate, EntityOut, EntityUpdate
from app.services import entity_service

router = APIRouter(
    prefix="/api/entities",
    tags=["entities"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=List[EntityOut])
def list_entities(
    type: Optional[EntityType] = Query(None, description="Filter by RESTAURANT or HOTEL"),
    is_active: Optional[bool] = Query(None),
    search: Optional[str] = Query(None, description="Case-insensitive search on entity name"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return entity_service.list_entities(
        db, entity_type=type, is_active=is_active, search=search, skip=skip, limit=limit
    )


@router.post("", response_model=EntityOut, status_code=status.HTTP_201_CREATED)
def create_entity(payload: EntityCreate, db: Session = Depends(get_db)):
    return entity_service.create_entity(db, payload)


@router.get("/{entity_id}", response_model=EntityOut)
def get_entity(entity_id: uuid.UUID, db: Session = Depends(get_db)):
    return entity_service.get_entity(db, entity_id)


@router.put("/{entity_id}", response_model=EntityOut)
def update_entity(entity_id: uuid.UUID, payload: EntityUpdate, db: Session = Depends(get_db)):
    return entity_service.update_entity(db, entity_id, payload)


@router.delete("/{entity_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entity(entity_id: uuid.UUID, db: Session = Depends(get_db)):
    entity_service.delete_entity(db, entity_id)
    return None