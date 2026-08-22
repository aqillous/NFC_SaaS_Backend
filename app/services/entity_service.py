"""
Entity business logic. Routers stay thin and delegate everything here.
"""
import random
import string
import uuid
from typing import Optional, Sequence

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entity import Entity, EntityType
from app.schemas.entity import EntityCreate, EntityOut, EntityUpdate

SLUG_LENGTH = 8
# Mixed-case alphanumeric, e.g. "a8Kx92Lm" — 62^8 ≈ 2.18 * 10^14 possible
# values, so random collisions are effectively impossible, but we still
# check-and-retry against the DB to guarantee uniqueness rather than assume it.
SLUG_ALPHABET = string.ascii_letters + string.digits
MAX_SLUG_GENERATION_ATTEMPTS = 10


def _generate_slug_candidate() -> str:
    # `random` (not `secrets`) is fine here: slugs aren't secrets, they're
    # public identifiers printed on physical NFC cards. Unpredictability
    # against guessing isn't the goal — non-sequential IDs are.
    return "".join(random.choices(SLUG_ALPHABET, k=SLUG_LENGTH))


def generate_unique_slug(db: Session) -> str:
    """Generate a random slug guaranteed not to collide with an existing entity."""
    for _ in range(MAX_SLUG_GENERATION_ATTEMPTS):
        candidate = _generate_slug_candidate()
        exists = db.scalar(select(Entity.id).where(Entity.slug == candidate))
        if exists is None:
            return candidate
    # Practically unreachable given the alphabet size, but fail loudly
    # rather than silently returning a colliding slug.
    raise RuntimeError("Failed to generate a unique slug after multiple attempts")


def build_nfc_url(slug: str) -> str:
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    return f"{base}/r/{slug}"


def _to_out(entity: Entity) -> EntityOut:
    return EntityOut(
        id=entity.id,
        name=entity.name,
        type=entity.type,
        google_review_url=entity.google_review_url,
        slug=entity.slug,
        is_active=entity.is_active,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
        nfc_url=build_nfc_url(entity.slug),
    )


def create_entity(db: Session, payload: EntityCreate) -> EntityOut:
    slug = generate_unique_slug(db)
    entity = Entity(
        name=payload.name,
        type=payload.type,
        google_review_url=payload.google_review_url,
        slug=slug,
        is_active=True,
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return _to_out(entity)


def get_entity_or_404(db: Session, entity_id: uuid.UUID) -> Entity:
    entity = db.get(Entity, entity_id)
    if entity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    return entity


def get_entity(db: Session, entity_id: uuid.UUID) -> EntityOut:
    return _to_out(get_entity_or_404(db, entity_id))


def get_entity_by_slug(db: Session, slug: str) -> Optional[Entity]:
    """Used by the (Phase 4) public redirect endpoint. Returns the ORM object, not a schema."""
    return db.scalar(select(Entity).where(Entity.slug == slug))


def list_entities(
    db: Session,
    entity_type: Optional[EntityType] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> Sequence[EntityOut]:
    stmt = select(Entity)
    if entity_type is not None:
        stmt = stmt.where(Entity.type == entity_type)
    if is_active is not None:
        stmt = stmt.where(Entity.is_active == is_active)
    if search:
        stmt = stmt.where(Entity.name.ilike(f"%{search}%"))
    stmt = stmt.order_by(Entity.created_at.desc()).offset(skip).limit(limit)

    entities = db.scalars(stmt).all()
    return [_to_out(e) for e in entities]


def count_entities(
    db: Session,
    entity_type: Optional[EntityType] = None,
    is_active: Optional[bool] = None,
) -> int:
    stmt = select(func.count()).select_from(Entity)
    if entity_type is not None:
        stmt = stmt.where(Entity.type == entity_type)
    if is_active is not None:
        stmt = stmt.where(Entity.is_active == is_active)
    return db.scalar(stmt) or 0


def update_entity(db: Session, entity_id: uuid.UUID, payload: EntityUpdate) -> EntityOut:
    entity = get_entity_or_404(db, entity_id)

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(entity, field, value)
    # `slug` is intentionally not a field on EntityUpdate — there is no code
    # path here that can change it. The NFC URL stays permanent even when
    # the Google Review URL, name, or type change.

    db.add(entity)
    db.commit()
    db.refresh(entity)
    return _to_out(entity)


def delete_entity(db: Session, entity_id: uuid.UUID) -> None:
    entity = get_entity_or_404(db, entity_id)
    db.delete(entity)
    db.commit()