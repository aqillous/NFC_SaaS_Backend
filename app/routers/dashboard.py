"""
Dashboard endpoint (platform-admin only).

Dashboard statistics are platform-wide aggregates, so they must only be
accessible to authenticated superusers. Entity/restaurant users must never
be able to read these totals.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_superuser
from app.schemas.dashboard import DashboardStats
from app.services import dashboard_service

router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(get_current_superuser)],
)


@router.get("/stats", response_model=DashboardStats)
def get_stats(db: Session = Depends(get_db)):
    return dashboard_service.get_dashboard_stats(db)