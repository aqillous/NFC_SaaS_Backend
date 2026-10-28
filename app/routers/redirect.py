"""
Public NFC review flow.

GET:
    /r/{slug}

Returns the information required by the frontend
to display the review/rating page.

POST:
    /r/{slug}/feedback

Saves the customer's feedback and returns JSON.

The backend does NOT redirect the customer.
The frontend controls the next step.
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)

from fastapi.responses import JSONResponse

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter

from app.schemas.feedback import FeedbackSubmit

from app.services.redirect_service import (
    evaluate_redirect,
    RedirectOutcome,
)

from app.services.feedback_service import (
    create_feedback,
)


router = APIRouter(
    tags=["redirect"]
)


@router.get(
    "/r/{slug}",
)
@limiter.limit(
    settings.REDIRECT_RATE_LIMIT
)
def get_nfc_page(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Returns the restaurant/entity information.

    The frontend uses this information to
    render the rating page.
    """

    result = evaluate_redirect(
        db,
        slug,
    )

    if (
        result.outcome
        == RedirectOutcome.NOT_FOUND
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )

    if (
        result.outcome
        == RedirectOutcome.UNAVAILABLE
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This NFC link is currently unavailable",
        )

    return {
        "entity": {
            "id": str(result.entity.id),
            "name": result.entity.name,
        },

        "google_review_url":
            result.google_review_url,
    }


@router.post(
    "/r/{slug}/feedback",
)
@limiter.limit("10/minute")
def submit_feedback(
    slug: str,
    payload: FeedbackSubmit,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Save customer feedback.

    IMPORTANT:
    This endpoint NEVER redirects.

    The frontend receives the result and
    decides what happens next.
    """

    result = evaluate_redirect(
        db,
        slug,
    )

    if (
        result.outcome
        == RedirectOutcome.NOT_FOUND
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )

    if (
        result.outcome
        == RedirectOutcome.UNAVAILABLE
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This NFC link is currently unavailable",
        )

    feedback, _ = create_feedback(
        db=db,

        entity=result.entity,

        quality=payload.quality,

        service=payload.service,

        taste=payload.taste,

        comment=payload.comment,

        reasons=payload.reasons,

        redirected_to_google=payload.redirected_to_google,

        user_agent=
            request.headers.get(
                "user-agent"
            ),

        ip_address=(
            request.client.host
            if request.client
            else None
        ),
    )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,

        content={
            "success": True,

            "feedback": {
                "id": str(feedback.id),

                "quality":
                    feedback.quality,

                "service":
                    feedback.service,

                "taste":
                    feedback.taste,

                "overall_score":
                    feedback.overall_score,

                "comment":
                    feedback.comment,

                "reasons":
                    feedback.reasons,

                "redirected_to_google":
                    feedback.redirected_to_google,

                "created_at":
                    feedback.created_at.isoformat(),
            },

            "google_review_url":
                result.google_review_url,
        },
    )