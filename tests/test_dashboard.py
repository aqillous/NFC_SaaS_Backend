import uuid

import pytest

from app.core.security import create_access_token, hash_password
from app.models.entity import Entity
from app.models.user import User


def _create_entity_user(db_session):
    entity = Entity(
        name="Restaurant User Test Entity",
        type="RESTAURANT",
        slug=f"dashboard-test-{uuid.uuid4().hex[:8]}",
        google_review_url="https://g.page/r/dashboard-test/review",
    )

    db_session.add(entity)
    db_session.flush()

    user = User(
        email="dashboard-restaurant@example.com",
        password_hash=hash_password("RestaurantPassword123!"),
        is_active=True,
        is_superuser=False,
        entity_id=entity.id,
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


@pytest.fixture
def entity_user(db_session):
    return _create_entity_user(db_session)


@pytest.fixture
def entity_user_headers(entity_user):
    token = create_access_token(subject=str(entity_user.id))
    return {"Authorization": f"Bearer {token}"}


def test_dashboard_stats_requires_superuser(
    client,
    entity_user_headers,
):
    response = client.get(
        "/api/dashboard/stats",
        headers=entity_user_headers,
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Superuser privileges required"


def test_dashboard_stats_requires_authentication(client):
    response = client.get("/api/dashboard/stats")

    assert response.status_code == 401


def test_dashboard_stats_allows_superuser(
    client,
    auth_headers,
):
    response = client.get(
        "/api/dashboard/stats",
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()

    expected_fields = {
        "total_entities",
        "total_restaurants",
        "total_hotels",
        "active_subscriptions",
        "expired_subscriptions",
        "expiring_soon",
        "scans_today",
        "scans_this_month",
        "total_feedback",
        "average_feedback_score",
        "average_quality",
        "average_service",
        "average_taste",
        "google_redirects",
        "internal_feedback",
        "google_redirect_rate",
        "feedback_today",
        "feedback_this_month",
    }

    assert set(data) == expected_fields
    assert data["total_entities"] == 0
    assert data["total_restaurants"] == 0
    assert data["total_hotels"] == 0