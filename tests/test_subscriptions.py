from datetime import datetime, timedelta, timezone

import pytest

from app.core.security import create_access_token, hash_password
from app.models.user import User


def _entity_payload(**overrides):
    payload = {
        "name": "Hilton Baku",
        "type": "HOTEL",
        "google_review_url": "https://g.page/r/abc123XYZ/review",
    }
    payload.update(overrides)
    return payload


def _create_entity(client, auth_headers, **overrides):
    resp = client.post(
        "/api/entities",
        json=_entity_payload(**overrides),
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _subscription_payload(
    entity_id: str,
    now: datetime | None = None,
    **overrides,
):
    now = now or datetime.now(timezone.utc)

    payload = {
        "entity_id": entity_id,
        "starts_at": _iso(now - timedelta(days=1)),
        "ends_at": _iso(now + timedelta(days=30)),
        "status": "ACTIVE",
    }

    payload.update(overrides)
    return payload


@pytest.fixture
def entity_user(db_session, admin_user):
    """Create a non-superuser venue account for authorization tests."""
    from app.models.entity import Entity

    entity = Entity(
        name="Restaurant User Test Entity",
        type="RESTAURANT",
        slug="rest-user-test",
        google_review_url="https://g.page/r/entity-user-test/review",
    )

    db_session.add(entity)
    db_session.flush()

    user = User(
        email="restaurant@example.com",
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
def entity_user_headers(entity_user):
    token = create_access_token(subject=str(entity_user.id))
    return {"Authorization": f"Bearer {token}"}


def test_create_subscription_success(client, auth_headers):
    entity = _create_entity(client, auth_headers)

    resp = client.post(
        "/api/subscriptions",
        json=_subscription_payload(entity["id"]),
        headers=auth_headers,
    )

    assert resp.status_code == 201

    data = resp.json()

    assert data["entity_id"] == entity["id"]
    assert data["status"] == "ACTIVE"
    assert data["is_currently_valid"] is True


def test_subscription_routes_require_superuser(
    client,
    entity_user_headers,
    auth_headers,
):
    entity = _create_entity(client, auth_headers)

    create_resp = client.post(
        "/api/subscriptions",
        json=_subscription_payload(entity["id"]),
        headers=auth_headers,
    )

    assert create_resp.status_code == 201

    subscription_id = create_resp.json()["id"]

    requests = [
        (
            "get",
            "/api/subscriptions",
        ),
        (
            "post",
            "/api/subscriptions",
            _subscription_payload(entity["id"]),
        ),
        (
            "get",
            f"/api/subscriptions/{subscription_id}",
        ),
        (
            "put",
            f"/api/subscriptions/{subscription_id}",
            {"status": "CANCELLED"},
        ),
        (
            "delete",
            f"/api/subscriptions/{subscription_id}",
        ),
    ]

    for method, url, *body in requests:
        kwargs = {
            "headers": entity_user_headers,
        }

        if body:
            kwargs["json"] = body[0]

        response = getattr(client, method)(url, **kwargs)

        assert response.status_code == 403, (
            method,
            url,
            response.text,
        )


def test_subscription_routes_require_authentication(client):
    requests = [
        (
            "get",
            "/api/subscriptions",
        ),
        (
            "post",
            "/api/subscriptions",
            _subscription_payload(
                "00000000-0000-0000-0000-000000000000"
            ),
        ),
        (
            "get",
            "/api/subscriptions/00000000-0000-0000-0000-000000000000",
        ),
        (
            "put",
            "/api/subscriptions/00000000-0000-0000-0000-000000000000",
            {"status": "CANCELLED"},
        ),
        (
            "delete",
            "/api/subscriptions/00000000-0000-0000-0000-000000000000",
        ),
    ]

    for method, url, *body in requests:
        kwargs = {}

        if body:
            kwargs["json"] = body[0]

        response = getattr(client, method)(url, **kwargs)

        assert response.status_code == 401, (
            method,
            url,
            response.text,
        )


def test_create_subscription_rejects_bad_date_order(
    client,
    auth_headers,
):
    entity = _create_entity(client, auth_headers)

    now = datetime.now(timezone.utc)

    payload = _subscription_payload(
        entity["id"],
        now=now,
        starts_at=_iso(now),
        ends_at=_iso(now - timedelta(days=1)),
    )

    resp = client.post(
        "/api/subscriptions",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 422


def test_create_subscription_unknown_entity_404(
    client,
    auth_headers,
):
    resp = client.post(
        "/api/subscriptions",
        json=_subscription_payload(
            "00000000-0000-0000-0000-000000000000"
        ),
        headers=auth_headers,
    )

    assert resp.status_code == 404


def test_expired_dates_report_not_currently_valid_even_if_status_active(
    client,
    auth_headers,
):
    """
    Regression test for the core business rule: status == ACTIVE is not
    enough — a subscription whose ends_at is in the past must report as
    invalid, because the redirect endpoint re-checks dates independently.
    """
    entity = _create_entity(client, auth_headers)

    now = datetime.now(timezone.utc)

    payload = _subscription_payload(
        entity["id"],
        now=now,
        starts_at=_iso(now - timedelta(days=60)),
        ends_at=_iso(now - timedelta(days=1)),
        status="ACTIVE",
    )

    resp = client.post(
        "/api/subscriptions",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 201
    assert resp.json()["is_currently_valid"] is False


def test_update_subscription_dates(client, auth_headers):
    entity = _create_entity(client, auth_headers)

    create_resp = client.post(
        "/api/subscriptions",
        json=_subscription_payload(entity["id"]),
        headers=auth_headers,
    )

    assert create_resp.status_code == 201

    sub_id = create_resp.json()["id"]

    resp = client.put(
        f"/api/subscriptions/{sub_id}",
        json={"status": "CANCELLED"},
        headers=auth_headers,
    )

    assert resp.status_code == 200

    data = resp.json()

    assert data["status"] == "CANCELLED"
    assert data["is_currently_valid"] is False


def test_delete_subscription(client, auth_headers):
    entity = _create_entity(client, auth_headers)

    create_resp = client.post(
        "/api/subscriptions",
        json=_subscription_payload(entity["id"]),
        headers=auth_headers,
    )

    assert create_resp.status_code == 201

    sub_id = create_resp.json()["id"]

    resp = client.delete(
        f"/api/subscriptions/{sub_id}",
        headers=auth_headers,
    )

    assert resp.status_code == 204

    resp = client.get(
        f"/api/subscriptions/{sub_id}",
        headers=auth_headers,
    )

    assert resp.status_code == 404


def test_list_subscriptions_filter_by_entity(
    client,
    auth_headers,
):
    entity_a = _create_entity(
        client,
        auth_headers,
        name="Place A",
    )

    entity_b = _create_entity(
        client,
        auth_headers,
        name="Place B",
    )

    for entity in (entity_a, entity_b):
        resp = client.post(
            "/api/subscriptions",
            json=_subscription_payload(entity["id"]),
            headers=auth_headers,
        )

        assert resp.status_code == 201

    resp = client.get(
        f"/api/subscriptions?entity_id={entity_a['id']}",
        headers=auth_headers,
    )

    assert resp.status_code == 200

    data = resp.json()

    assert len(data) == 1
    assert data[0]["entity_id"] == entity_a["id"]