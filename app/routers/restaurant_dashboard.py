import uuid

from fastapi import (
    APIRouter,
    Depends,
    Query,
    HTTPException,
    status,
)

from sqlalchemy.orm import Session

from app.core.database import get_db

from app.dependencies.entity_access import (
    require_entity_user,
)

from app.models.user import User

from app.services.entity_service import (
    get_entity_or_404,
)

from app.services.feedback_service import (
    get_dashboard,
    list_feedback,
)

from app.schemas.feedback import (
    FeedbackOut,
    RestaurantDashboard,
)


router = APIRouter(
    prefix="/api/restaurant",
    tags=["restaurant-dashboard"],
)


def _resolve_entity_id(
    current_user: User,
    entity_id: uuid.UUID | None,
) -> uuid.UUID:

    # Restaurant account
    if current_user.entity_id is not None:

        # Prevent accessing another restaurant
        if (
            entity_id is not None
            and entity_id != current_user.entity_id
        ):

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You can only access "
                    "your own entity"
                ),
            )

        return current_user.entity_id

    # Superadmin
    if (
        current_user.is_superuser
        and entity_id is not None
    ):

        return entity_id

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=(
            "entity_id is required "
            "for a platform admin"
        ),
    )


@router.get(
    "/dashboard",
    response_model=RestaurantDashboard,
)
def dashboard(
    entity_id: uuid.UUID | None = Query(None),

    days: int = Query(
        30,
        ge=1,
        le=365,
    ),

    current_user: User = Depends(
        require_entity_user
    ),

    db: Session = Depends(get_db),
):

    target_id = _resolve_entity_id(
        current_user,
        entity_id,
    )

    entity = get_entity_or_404(
        db,
        target_id,
    )

    return get_dashboard(
        db,
        entity,
        days=days,
    )


@router.get(
    "/feedback",
    response_model=list[FeedbackOut],
)
def feedback(
    entity_id: uuid.UUID | None = Query(None),

    skip: int = Query(
        0,
        ge=0,
    ),

    limit: int = Query(
        50,
        ge=1,
        le=200,
    ),

    current_user: User = Depends(
        require_entity_user
    ),

    db: Session = Depends(get_db),
):

    target_id = _resolve_entity_id(
        current_user,
        entity_id,
    )

    get_entity_or_404(
        db,
        target_id,
    )

    return list_feedback(
        db,
        target_id,
        skip=skip,
        limit=limit,
    )