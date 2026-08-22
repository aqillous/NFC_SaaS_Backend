"""
Public NFC redirect endpoint.

GET /r/{slug}  — NO authentication. This is the URL printed on the physical
NFC card, tapped by anonymous customers. It must:
  - 404 if the slug doesn't exist
  - show a plain "unavailable" page if the entity is inactive, has no
    subscription, or the subscription is expired/cancelled/out of date range
  - 302 redirect to the entity's Google Review URL if (and only if) the
    subscription is currently valid, logging the tap on the way out

Rate-limited to protect against slug-enumeration / scraping abuse.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.config import settings
from app.services.redirect_service import RedirectOutcome, evaluate_redirect, log_redirect

router = APIRouter(tags=["redirect"])


_UNAVAILABLE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Service Unavailable</title>
  <meta name="robots" content="noindex" />
  <style>
    body {{
      margin: 0;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      background: #0f172a;
      color: #e2e8f0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      text-align: center;
      padding: 24px;
      box-sizing: border-box;
    }}
    .card {{ max-width: 420px; }}
    h1 {{ font-size: 1.25rem; font-weight: 600; margin: 0 0 8px; }}
    p {{ margin: 0; color: #94a3b8; font-size: 0.95rem; line-height: 1.5; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>This service is currently unavailable</h1>
    <p>Please contact the venue directly, or try again later.</p>
  </div>
</body>
</html>
"""


@router.get("/r/{slug}")
@limiter.limit(settings.REDIRECT_RATE_LIMIT)
def redirect_nfc_card(slug: str, request: Request, db: Session = Depends(get_db)):
    """
    slowapi's @limiter.limit decorator requires a `request: Request`
    parameter to be present on the route function — that's how it reads the
    client's IP to key the rate limit bucket.
    """
    result = evaluate_redirect(db, slug)

    if result.outcome == RedirectOutcome.NOT_FOUND:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    if result.outcome == RedirectOutcome.UNAVAILABLE:
        return HTMLResponse(content=_UNAVAILABLE_HTML, status_code=status.HTTP_200_OK)

    # RedirectOutcome.VALID — log the tap, then send the customer to Google.
    log_redirect(
        db,
        entity_id=result.entity.id,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    return RedirectResponse(url=result.google_review_url, status_code=status.HTTP_302_FOUND)