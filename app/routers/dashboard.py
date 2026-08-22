"""
Dashboard endpoint (admin-only). Read-only aggregate stats for the overview page.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_user
from app.schemas.dashboard import DashboardStats
from app.services import dashboard_service

router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/stats", response_model=DashboardStats)
def get_stats(db: Session = Depends(get_db)):
    return dashboard_service.get_dashboard_stats(db)
