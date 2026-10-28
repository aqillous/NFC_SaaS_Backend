"""
Public NFC review flow.

GET:
    /r/{slug}

Returns the information required by the frontend
to display the review/rating page.

GET:
    /r/{slug}/google

Logs a Google review link open and redirects to the configured URL.

POST:
    /r/{slug}/feedback

Saves the customer's feedback and returns JSON.
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)

from fastapi.responses import JSONResponse, RedirectResponse

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter

from app.schemas.feedback import FeedbackSubmit

from app.services.redirect_service import (
    evaluate_redirect,
    RedirectOutcome,
    log_redirect,
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


@router.get(
    "/r/{slug}/google",
)
@limiter.limit(
    settings.REDIRECT_RATE_LIMIT
)
def redirect_to_google(
    slug: str,
    request: Request,
    db: Session = Depends(get_db),
):
    result = evaluate_redirect(db, slug)

    if result.outcome == RedirectOutcome.NOT_FOUND:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )

    if result.outcome == RedirectOutcome.UNAVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This NFC link is currently unavailable",
        )

    log_redirect(
        db=db,
        entity_id=result.entity.id,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )

    return RedirectResponse(
        url=result.google_review_url,
        status_code=status.HTTP_302_FOUND,
    )


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