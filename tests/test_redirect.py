from datetime import datetime, timedelta, timezone

from app.models.redirect_log import RedirectLog


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


def _create_subscription(
    client,
    auth_headers,
    entity_id,
    *,
    status="ACTIVE",
    starts_delta=-1,
    ends_delta=30,
):
    now = datetime.now(timezone.utc)

    payload = {
        "entity_id": entity_id,
        "starts_at": (
            now + timedelta(days=starts_delta)
        ).isoformat(),
        "ends_at": (
            now + timedelta(days=ends_delta)
        ).isoformat(),
        "status": status,
    }

    resp = client.post(
        "/api/subscriptions",
        json=payload,
        headers=auth_headers,
    )

    assert resp.status_code == 201

    return resp.json()


def test_active_subscription_returns_nfc_page(
    client,
    auth_headers,
):
    entity = _create_entity(
        client,
        auth_headers,
    )

    _create_subscription(
        client,
        auth_headers,
        entity["id"],
    )

    resp = client.get(
        f"/r/{entity['slug']}",
    )

    assert resp.status_code == 200

    data = resp.json()

    assert data["entity"]["id"] == entity["id"]
    assert data["entity"]["name"] == entity["name"]
    assert (
        data["google_review_url"]
        == entity["google_review_url"]
    )


def test_expired_subscription_returns_unavailable(
    client,
    auth_headers,
):
    entity = _create_entity(
        client,
        auth_headers,
    )

    # status is ACTIVE, but the date range is in the past.
    # The live date check must still make the NFC link unavailable.
    _create_subscription(
        client,
        auth_headers,
        entity["id"],
        starts_delta=-60,
        ends_delta=-1,
    )

    resp = client.get(
        f"/r/{entity['slug']}",
    )

    assert resp.status_code == 403

    data = resp.json()

    assert (
        data["detail"]
        == "This NFC link is currently unavailable"
    )


def test_cancelled_subscription_returns_unavailable(
    client,
    auth_headers,
):
    entity = _create_entity(
        client,
        auth_headers,
    )

    _create_subscription(
        client,
        auth_headers,
        entity["id"],
        status="CANCELLED",
    )

    resp = client.get(
        f"/r/{entity['slug']}",
    )

    assert resp.status_code == 403

    data = resp.json()

    assert (
        data["detail"]
        == "This NFC link is currently unavailable"
    )


def test_inactive_entity_returns_unavailable(
    client,
    auth_headers,
):
    entity = _create_entity(
        client,
        auth_headers,
    )

    _create_subscription(
        client,
        auth_headers,
        entity["id"],
    )

    resp = client.put(
        f"/api/entities/{entity['id']}",
        json={"is_active": False},
        headers=auth_headers,
    )

    assert resp.status_code == 200

    resp = client.get(
        f"/r/{entity['slug']}",
    )

    assert resp.status_code == 403

    data = resp.json()

    assert (
        data["detail"]
        == "This NFC link is currently unavailable"
    )


def test_entity_with_no_subscription_returns_unavailable(
    client,
    auth_headers,
):
    entity = _create_entity(
        client,
        auth_headers,
    )

    resp = client.get(
        f"/r/{entity['slug']}",
    )

    assert resp.status_code == 403

    data = resp.json()

    assert (
        data["detail"]
        == "This NFC link is currently unavailable"
    )


def test_unavailable_nfc_page_does_not_expose_google_url(
    client,
    auth_headers,
):
    entity = _create_entity(
        client,
        auth_headers,
    )

    resp = client.get(
        f"/r/{entity['slug']}",
    )

    assert resp.status_code == 403

    data = resp.json()

    assert "google_review_url" not in data


def test_nonexistent_slug_returns_404(client):
    resp = client.get(
        "/r/doesnotexist",
    )

    assert resp.status_code == 404

    data = resp.json()

    assert data["detail"] == "Not found"


def test_changing_google_review_url_keeps_same_nfc_url(
    client,
    auth_headers,
):
    entity = _create_entity(
        client,
        auth_headers,
    )

    _create_subscription(
        client,
        auth_headers,
        entity["id"],
    )

    original_slug = entity["slug"]

    new_google_url = (
        "https://maps.app.goo.gl/newlink123"
    )

    resp = client.put(
        f"/api/entities/{entity['id']}",
        json={
            "google_review_url": new_google_url,
        },
        headers=auth_headers,
    )

    assert resp.status_code == 200

    updated = resp.json()

    assert updated["slug"] == original_slug
    assert updated["nfc_url"].endswith(
        f"/r/{original_slug}"
    )

    # The physical NFC URL remains unchanged,
    # while the Google destination can change.
    resp = client.get(
        f"/r/{original_slug}",
    )

    assert resp.status_code == 200

    data = resp.json()

    assert data["google_review_url"] == new_google_url


def test_nfc_page_does_not_require_auth(
    client,
    auth_headers,
):
    entity = _create_entity(
        client,
        auth_headers,
    )

    _create_subscription(
        client,
        auth_headers,
        entity["id"],
    )

    # Customer NFC taps are anonymous.
    resp = client.get(
        f"/r/{entity['slug']}",
    )

    assert resp.status_code == 200

    data = resp.json()

    assert data["entity"]["id"] == entity["id"]


def test_google_review_route_logs_and_redirects(
    client,
    auth_headers,
    db_session,
):
    entity = _create_entity(client, auth_headers)
    _create_subscription(client, auth_headers, entity["id"])

    response = client.get(
        f"/r/{entity['slug']}/google",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert (
        response.headers["location"]
        == entity["google_review_url"]
    )
    assert (
        db_session.query(RedirectLog)
        .filter_by(entity_id=entity["id"])
        .count()
        == 1
    )

    stats = client.get(
        "/api/dashboard/stats",
        headers=auth_headers,
    ).json()
    assert stats["google_redirects"] == 1
    assert stats["scans_today"] == 1

    entity_dashboard = client.get(
        "/api/restaurant/dashboard",
        params={"entity_id": entity["id"]},
        headers=auth_headers,
    ).json()["stats"]
    assert entity_dashboard["google_redirects"] == 1
    assert entity_dashboard["google_redirect_rate"] == 100


def test_feedback_submission_does_not_mark_google_redirect(
    client,
    auth_headers,
):
    entity = _create_entity(client, auth_headers)
    _create_subscription(client, auth_headers, entity["id"])

    response = client.post(
        f"/r/{entity['slug']}/feedback",
        json={
            "quality": 1,
            "service": 1,
            "taste": 1,
            "redirected_to_google": True,
        },
    )

    assert response.status_code == 201
    data = response.json()["feedback"]
    assert data["overall_score"] == 1
    assert data["redirected_to_google"] is False
    assert data["reasons"] == []


def test_business_feedback_saves_reasons_and_comment(
    client,
    auth_headers,
):
    entity = _create_entity(client, auth_headers)
    _create_subscription(client, auth_headers, entity["id"])

    response = client.post(
        f"/r/{entity['slug']}/feedback",
        json={
            "quality": 3,
            "service": 3,
            "taste": 3,
            "comment": "Please improve the wait time.",
            "reasons": ["service_speed", "staff_attitude"],
        },
    )

    assert response.status_code == 201
    data = response.json()["feedback"]
    assert data["reasons"] == ["service_speed", "staff_attitude"]
    assert data["comment"] == "Please improve the wait time."
    assert data["redirected_to_google"] is False


def test_feedback_rejects_unknown_reasons(
    client,
    auth_headers,
):
    entity = _create_entity(client, auth_headers)
    _create_subscription(client, auth_headers, entity["id"])

    response = client.post(
        f"/r/{entity['slug']}/feedback",
        json={
            "quality": 3,
            "service": 3,
            "taste": 3,
            "reasons": ["other"],
        },
    )

    assert response.status_code == 422