def test_login_success(client, admin_user):
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "StrongPassword123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, admin_user):
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "WrongPassword"},
    )
    assert response.status_code == 401


def test_login_unknown_email(client):
    response = client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "whatever"},
    )
    assert response.status_code == 401


def test_me_requires_token(client):
    response = client.get("/api/auth/me")
    assert response.status_code in (401, 403)


def test_me_with_valid_token(client, admin_user):
    login_resp = client.post(
        "/api/auth/login",
        json={"email": "admin@example.com", "password": "StrongPassword123!"},
    )
    token = login_resp.json()["access_token"]

    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    data = me_resp.json()
    assert data["email"] == "admin@example.com"
    assert data["is_superuser"] is True


def test_me_with_invalid_token(client):
    response = client.get("/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_inactive_user_cannot_login(client, db_session):
    from app.core.security import hash_password
    from app.models.user import User

    user = User(
        email="inactive@example.com",
        password_hash=hash_password("Password123!"),
        is_active=False,
        is_superuser=False,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        json={"email": "inactive@example.com", "password": "Password123!"},
    )
    assert response.status_code == 403
