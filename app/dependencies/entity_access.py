from fastapi import (
    Depends,
    HTTPException,
    status,
)

from app.dependencies.auth import get_current_user
from app.models.user import User


def require_entity_user(
    current_user: User = Depends(
        get_current_user
    ),
) -> User:

    """
    Restaurant/hotel dashboard access.

    Normal entity users must have entity_id.

    Platform admins/superusers can have entity_id=NULL.
    """

    if (
        current_user.entity_id is None
        and not current_user.is_superuser
    ):

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "This account is not linked "
                "to an entity"
            ),
        )

    return current_user