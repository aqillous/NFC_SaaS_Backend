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


def _create_subscription(client, auth_headers, entity_id, *, status="ACTIVE", starts_delta=-1, ends_delta=30):
    now = datetime.now(timezone.utc)
    payload = {
        "entity_id": entity_id,
        "starts_at": (now + timedelta(days=starts_delta)).isoformat(),
        "ends_at": (now + timedelta(days=ends_delta)).isoformat(),
        "status": status,
    }
    resp = client.post("/api/subscriptions", json=payload, headers=auth_headers)
    assert resp.status_code == 201
    return resp.json()


def test_active_subscription_redirects_to_google(client, auth_headers):
    entity = _create_entity(client, auth_headers)
    _create_subscription(client, auth_headers, entity["id"])

    resp = client.get(f"/r/{entity['slug']}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == entity["google_review_url"]


def test_expired_subscription_does_not_redirect(client, auth_headers):
    entity = _create_entity(client, auth_headers)
    # status says ACTIVE, but the date range is in the past — the endpoint
    # must catch this even though the status field alone would say "fine".
    _create_subscription(client, auth_headers, entity["id"], starts_delta=-60, ends_delta=-1)

    resp = client.get(f"/r/{entity['slug']}", follow_redirects=False)
    assert resp.status_code == 200
    assert "unavailable" in resp.text.lower()


def test_cancelled_subscription_does_not_redirect(client, auth_headers):
    entity = _create_entity(client, auth_headers)
    _create_subscription(client, auth_headers, entity["id"], status="CANCELLED")

    resp = client.get(f"/r/{entity['slug']}", follow_redirects=False)
    assert resp.status_code == 200
    assert "unavailable" in resp.text.lower()


def test_inactive_entity_does_not_redirect(client, auth_headers):
    entity = _create_entity(client, auth_headers)
    _create_subscription(client, auth_headers, entity["id"])

    resp = client.put(
        f"/api/entities/{entity['id']}", json={"is_active": False}, headers=auth_headers
    )
    assert resp.status_code == 200

    resp = client.get(f"/r/{entity['slug']}", follow_redirects=False)
    assert resp.status_code == 200
    assert "unavailable" in resp.text.lower()


def test_entity_with_no_subscription_does_not_redirect(client, auth_headers):
    entity = _create_entity(client, auth_headers)

    resp = client.get(f"/r/{entity['slug']}", follow_redirects=False)
    assert resp.status_code == 200
    assert "unavailable" in resp.text.lower()


def test_nonexistent_slug_returns_404(client, auth_headers):
    resp = client.get("/r/doesnotexist", follow_redirects=False)
    assert resp.status_code == 404


def test_changing_google_review_url_keeps_same_nfc_url(client, auth_headers):
    entity = _create_entity(client, auth_headers)
    _create_subscription(client, auth_headers, entity["id"])
    original_slug = entity["slug"]

    resp = client.put(
        f"/api/entities/{entity['id']}",
        json={"google_review_url": "https://maps.app.goo.gl/newlink123"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    updated = resp.json()
    assert updated["slug"] == original_slug
    assert updated["nfc_url"].endswith(f"/r/{original_slug}")

    # The public URL must still work and now redirect to the *new* URL.
    resp = client.get(f"/r/{original_slug}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://maps.app.goo.gl/newlink123"


def test_redirect_does_not_require_auth(client, auth_headers):
    entity = _create_entity(client, auth_headers)
    _create_subscription(client, auth_headers, entity["id"])

    # No Authorization header at all.
    resp = client.get(f"/r/{entity['slug']}", follow_redirects=False)
    assert resp.status_code == 302