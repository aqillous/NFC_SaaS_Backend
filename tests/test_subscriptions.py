from datetime import datetime, timedelta, timezone


def _entity_payload(**overrides):
    payload = {
        "name": "Hilton Baku",
        "type": "HOTEL",
        "google_review_url": "https://g.page/r/abc123XYZ/review",
    }
    payload.update(overrides)
    return payload


def _create_entity(client, auth_headers, **overrides):
    resp = client.post("/api/entities", json=_entity_payload(**overrides), headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def test_create_subscription_success(client, auth_headers):
    entity = _create_entity(client, auth_headers)
    now = datetime.now(timezone.utc)
    payload = {
        "entity_id": entity["id"],
        "starts_at": _iso(now - timedelta(days=1)),
        "ends_at": _iso(now + timedelta(days=30)),
        "status": "ACTIVE",
    }
    resp = client.post("/api/subscriptions", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["entity_id"] == entity["id"]
    assert data["status"] == "ACTIVE"
    assert data["is_currently_valid"] is True


def test_create_subscription_requires_auth(client):
    resp = client.post(
        "/api/subscriptions",
        json={
            "entity_id": "00000000-0000-0000-0000-000000000000",
            "starts_at": _iso(datetime.now(timezone.utc)),
            "ends_at": _iso(datetime.now(timezone.utc) + timedelta(days=1)),
        },
    )
    assert resp.status_code in (401, 403)


def test_create_subscription_rejects_bad_date_order(client, auth_headers):
    entity = _create_entity(client, auth_headers)
    now = datetime.now(timezone.utc)
    payload = {
        "entity_id": entity["id"],
        "starts_at": _iso(now),
        "ends_at": _iso(now - timedelta(days=1)),  # ends before it starts
    }
    resp = client.post("/api/subscriptions", json=payload, headers=auth_headers)
    assert resp.status_code == 422


def test_create_subscription_unknown_entity_404(client, auth_headers):
    now = datetime.now(timezone.utc)
    payload = {
        "entity_id": "00000000-0000-0000-0000-000000000000",
        "starts_at": _iso(now),
        "ends_at": _iso(now + timedelta(days=1)),
    }
    resp = client.post("/api/subscriptions", json=payload, headers=auth_headers)
    assert resp.status_code == 404


def test_expired_dates_report_not_currently_valid_even_if_status_active(client, auth_headers):
    """
    Regression test for the core business rule: status == ACTIVE is not
    enough — a subscription whose ends_at is in the past must report as
    invalid, because the redirect endpoint re-checks dates independently.
    """
    entity = _create_entity(client, auth_headers)
    now = datetime.now(timezone.utc)
    payload = {
        "entity_id": entity["id"],
        "starts_at": _iso(now - timedelta(days=60)),
        "ends_at": _iso(now - timedelta(days=1)),  # already expired
        "status": "ACTIVE",
    }
    resp = client.post("/api/subscriptions", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    assert resp.json()["is_currently_valid"] is False


def test_update_subscription_dates(client, auth_headers):
    entity = _create_entity(client, auth_headers)
    now = datetime.now(timezone.utc)
    create_resp = client.post(
        "/api/subscriptions",
        json={
            "entity_id": entity["id"],
            "starts_at": _iso(now),
            "ends_at": _iso(now + timedelta(days=10)),
        },
        headers=auth_headers,
    )
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
    now = datetime.now(timezone.utc)
    create_resp = client.post(
        "/api/subscriptions",
        json={
            "entity_id": entity["id"],
            "starts_at": _iso(now),
            "ends_at": _iso(now + timedelta(days=10)),
        },
        headers=auth_headers,
    )
    sub_id = create_resp.json()["id"]

    resp = client.delete(f"/api/subscriptions/{sub_id}", headers=auth_headers)
    assert resp.status_code == 204

    resp = client.get(f"/api/subscriptions/{sub_id}", headers=auth_headers)
    assert resp.status_code == 404


def test_list_subscriptions_filter_by_entity(client, auth_headers):
    entity_a = _create_entity(client, auth_headers, name="Place A")
    entity_b = _create_entity(client, auth_headers, name="Place B")
    now = datetime.now(timezone.utc)

    for entity in (entity_a, entity_b):
        client.post(
            "/api/subscriptions",
            json={
                "entity_id": entity["id"],
                "starts_at": _iso(now),
                "ends_at": _iso(now + timedelta(days=10)),
            },
            headers=auth_headers,
        )

    resp = client.get(f"/api/subscriptions?entity_id={entity_a['id']}", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["entity_id"] == entity_a["id"]