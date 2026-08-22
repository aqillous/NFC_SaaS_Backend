from pydantic import BaseModel


class DashboardStats(BaseModel):
    total_entities: int
    total_restaurants: int
    total_hotels: int
    active_subscriptions: int
    expired_subscriptions: int
    expiring_soon: int  # currently-valid subscriptions ending within 7 days
    scans_today: int
    scans_this_month: int
