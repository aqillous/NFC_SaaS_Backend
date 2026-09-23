import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    is_active: bool
    is_superuser: bool
    entity_id: uuid.UUID | None
    created_at: datetime


class EntityUserCreate(BaseModel):
    """
    Creates a login account for a restaurant/hotel.

    entity_id is NOT accepted here because it comes
    from the URL:

        /api/entities/{entity_id}/users
    """

    email: EmailStr

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
    )


# Keep these only if you are using the generic
# Users page for admin user management.

class UserAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    is_active: bool
    is_superuser: bool
    entity_id: uuid.UUID | None
    created_at: datetime
    entity_name: str | None = None


class PasswordReset(BaseModel):
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
    )


class UserStatusUpdate(BaseModel):
    is_active: bool