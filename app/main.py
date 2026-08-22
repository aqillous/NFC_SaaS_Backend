from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.rate_limit import limiter
from app.routers import auth as auth_router
from app.routers import dashboard as dashboard_router
from app.routers import entities as entities_router
from app.routers import redirect as redirect_router
from app.routers import subscriptions as subscriptions_router

app = FastAPI(
    title=settings.APP_NAME,
    description="NFC-based Google Review management platform — admin API",
    version="0.1.0",
    debug=settings.DEBUG,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(dashboard_router.router)
app.include_router(entities_router.router)
app.include_router(subscriptions_router.router)
app.include_router(redirect_router.router)


@app.get("/health", tags=["health"])
def health_check() -> dict:
    return {"status": "ok", "environment": settings.ENVIRONMENT}