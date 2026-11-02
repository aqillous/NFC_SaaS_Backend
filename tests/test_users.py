import uuid

from app.core.security import verify_password
from app.models.entity import Entity
from app.models.user import User


def _entity(db_session):
    entity = Entity(
        name="Cafe Sunrise",
        type="RESTAURANT",
        google_review_url="https://g.page/r/abc123XYZ/review",
        slug="sunrise1",
        is_active=True,
    )
    db_session.add(entity)
    db_session.commit()
    db_session.refresh(entity)
    return entity


def test_list_users_requires_superuser(client):
    response = client.get("/api/users")
    assert response.status_code in (401, 403)


def test_list_users_includes_entity_name(client, auth_headers, db_session):
    entity = _entity(db_session)
    db_session.add(
        User(
            email="restaurant@example.com",
            password_hash="hashed",
            is_active=True,
            is_superuser=False,
            entity_id=entity.id,
        )
    )
    db_session.commit()

    response = client.get("/api/users", headers=auth_headers)

    assert response.status_code == 200
    users = response.json()
    restaurant_user = next(
        user for user in users if user["email"] == "restaurant@example.com"
    )
    assert restaurant_user["entity_name"] == "Cafe Sunrise"


def test_create_entity_user(client, auth_headers, db_session):
    entity = _entity(db_session)

    response = client.post(
        "/api/users",
        headers=auth_headers,
        json={
            "email": "new-user@example.com",
            "password": "StrongPassword123!",
            "entity_id": str(entity.id),
            "is_superuser": False,
        },
    )

    assert response.status_code == 201
    assert response.json()["entity_name"] == "Cafe Sunrise"
    user = db_session.query(User).filter_by(email="new-user@example.com").one()
    assert verify_password("StrongPassword123!", user.password_hash)
    assert user.is_superuser is False


def test_create_platform_admin(client, auth_headers):
    response = client.post(
        "/api/users",
        headers=auth_headers,
        json={
            "email": "new-admin@example.com",
            "password": "StrongPassword123!",
            "entity_id": None,
            "is_superuser": True,
        },
    )

    assert response.status_code == 201
    assert response.json()["is_superuser"] is True
    assert response.json()["entity_id"] is None


def test_create_user_requires_entity_for_non_admin(client, auth_headers):
    response = client.post(
        "/api/users",
        headers=auth_headers,
        json={
            "email": "unassigned@example.com",
            "password": "StrongPassword123!",
            "entity_id": None,
            "is_superuser": False,
        },
    )

    assert response.status_code == 422


def test_user_management_status_and_password_reset(
    client, auth_headers, admin_user, db_session
):
    target_user = User(
        email="target@example.com",
        password_hash="hashed",
        is_active=True,
        is_superuser=False,
    )
    db_session.add(target_user)
    db_session.commit()
    db_session.refresh(target_user)

    status_response = client.patch(
        f"/api/users/{target_user.id}",
        headers=auth_headers,
        json={"is_active": False},
    )
    assert status_response.status_code == 200
    assert status_response.json()["is_active"] is False

    reset_response = client.post(
        f"/api/users/{target_user.id}/reset-password",
        headers=auth_headers,
        json={"password": "NewStrongPassword123!"},
    )
    assert reset_response.status_code == 200
    db_session.refresh(target_user)
    assert verify_password("NewStrongPassword123!", target_user.password_hash)


def test_user_mutations_return_404_for_unknown_user(client, auth_headers):
    missing_id = uuid.uuid4()

    status_response = client.patch(
        f"/api/users/{missing_id}",
        headers=auth_headers,
        json={"is_active": False},
    )
    reset_response = client.post(
        f"/api/users/{missing_id}/reset-password",
        headers=auth_headers,
        json={"password": "NewStrongPassword123!"},
    )

    assert status_response.status_code == 404
    assert reset_response.status_code == 404
