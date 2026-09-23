from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_entities: int
    total_restaurants: int
    total_hotels: int

    active_subscriptions: int
    expired_subscriptions: int
    expiring_soon: int

    scans_today: int
    scans_this_month: int

    # Feedback overview
    total_feedback: int
    average_feedback_score: float

    average_quality: float
    average_service: float
    average_taste: float

    google_redirects: int
    internal_feedback: int
    google_redirect_rate: float

    feedback_today: int
    feedback_this_month: int