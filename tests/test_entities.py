import uuid


def _entity_payload(**overrides):
    payload = {
        "name": "Hilton Baku",
        "type": "HOTEL",
        "google_review_url": "https://g.page/r/abc123XYZ/review",
    }
    payload.update(overrides)
    return payload


def test_create_entity_success(client, auth_headers):
    resp = client.post("/api/entities", json=_entity_payload(), headers=auth_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Hilton Baku"
    assert data["type"] == "HOTEL"
    assert data["is_active"] is True
    assert len(data["slug"]) == 8
    assert data["nfc_url"].endswith(f"/r/{data['slug']}")


def test_create_entity_requires_auth(client):
    resp = client.post("/api/entities", json=_entity_payload())
    assert resp.status_code in (401, 403)


def test_create_entity_rejects_non_google_url(client, auth_headers):
    payload = _entity_payload(google_review_url="https://example.com/not-google")
    resp = client.post("/api/entities", json=payload, headers=auth_headers)
    assert resp.status_code == 422


def test_create_entity_rejects_missing_fields(client, auth_headers):
    resp = client.post("/api/entities", json={"name": "Missing Fields"}, headers=auth_headers)
    assert resp.status_code == 422


def test_slug_is_unique_across_many_entities(client, auth_headers):
    slugs = set()
    for i in range(25):
        resp = client.post(
            "/api/entities",
            json=_entity_payload(name=f"Place {i}"),
            headers=auth_headers,
        )
        assert resp.status_code == 201
        slugs.add(resp.json()["slug"])
    assert len(slugs) == 25  # every generated slug was unique


def test_slug_is_not_based_on_id(client, auth_headers):
    resp = client.post("/api/entities", json=_entity_payload(), headers=auth_headers)
    data = resp.json()
    assert data["slug"] != str(data["id"])
    assert data["slug"] not in str(data["id"])


def test_changing_google_review_url_keeps_same_slug(client, auth_headers):
    create_resp = client.post("/api/entities", json=_entity_payload(), headers=auth_headers)
    entity = create_resp.json()
    original_slug = entity["slug"]
    original_nfc_url = entity["nfc_url"]

    update_resp = client.put(
        f"/api/entities/{entity['id']}",
        json={"google_review_url": "https://g.page/r/differentReviewLink/review"},
        headers=auth_headers,
    )
    assert update_resp.status_code == 200
    updated = update_resp.json()
    assert updated["slug"] == original_slug
    assert updated["nfc_url"] == original_nfc_url
    assert updated["google_review_url"] == "https://g.page/r/differentReviewLink/review"


def test_update_entity_active_state(client, auth_headers):
    create_resp = client.post("/api/entities", json=_entity_payload(), headers=auth_headers)
    entity_id = create_resp.json()["id"]

    update_resp = client.put(
        f"/api/entities/{entity_id}", json={"is_active": False}, headers=auth_headers
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["is_active"] is False


def test_get_entity_not_found(client, auth_headers):
    resp = client.get(f"/api/entities/{uuid.uuid4()}", headers=auth_headers)
    assert resp.status_code == 404


def test_delete_entity(client, auth_headers):
    create_resp = client.post("/api/entities", json=_entity_payload(), headers=auth_headers)
    entity_id = create_resp.json()["id"]

    delete_resp = client.delete(f"/api/entities/{entity_id}", headers=auth_headers)
    assert delete_resp.status_code == 204

    get_resp = client.get(f"/api/entities/{entity_id}", headers=auth_headers)
    assert get_resp.status_code == 404


def test_list_entities_filters_by_type(client, auth_headers):
    client.post("/api/entities", json=_entity_payload(name="R1", type="RESTAURANT"), headers=auth_headers)
    client.post("/api/entities", json=_entity_payload(name="H1", type="HOTEL"), headers=auth_headers)

    resp = client.get("/api/entities?type=HOTEL", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["type"] == "HOTEL"


def test_list_entities_search_by_name(client, auth_headers):
    client.post("/api/entities", json=_entity_payload(name="Marriott Downtown"), headers=auth_headers)
    client.post("/api/entities", json=_entity_payload(name="Cafe Sunrise"), headers=auth_headers)

    resp = client.get("/api/entities?search=marriott", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert "Marriott" in data[0]["name"]