from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from src.infrastructure.database.postgres.models import UserPermissionModel


@pytest.mark.django_db
def test_full_user_auth_lifecycle_and_activity_logging(in_memory_mongo_collection) -> None:
    client = APIClient()

    # 1. Invalid email returns 400 users-001
    bad_reg = client.post(
        "/api/v1/users/register",
        {"email": "bad-email", "password": "pw", "first_name": "A", "last_name": "B"},
        format="json",
    )
    assert bad_reg.status_code == 400
    assert bad_reg.json()["trace_id"] == "users-001"

    # 2. Register succeeds -> 201 + default user_permissions created
    reg = client.post(
        "/api/v1/users/register",
        {
            "email": "alice@example.com",
            "password": "secret-password",
            "first_name": "Alice",
            "last_name": "Smith",
        },
        format="json",
    )
    assert reg.status_code == 201
    user_id = reg.json()["id"]
    assert "password" not in reg.json()
    assert UserPermissionModel.objects.filter(user_id=user_id, permission="user").exists()

    # 3. Duplicate email returns 409 users-001
    dup = client.post(
        "/api/v1/users/register",
        {
            "email": "alice@example.com",
            "password": "secret-password",
            "first_name": "Alice",
            "last_name": "Smith",
        },
        format="json",
    )
    assert dup.status_code == 409
    assert dup.json()["trace_id"] == "users-001"

    # 4. Wrong password login returns 400 users-002 + logs failed login
    bad_login = client.post(
        "/api/v1/users/login",
        {"email": "alice@example.com", "password": "wrong"},
        format="json",
    )
    assert bad_login.status_code == 400
    assert bad_login.json()["trace_id"] == "users-002"

    # 5. Valid login returns 200 with user + token
    login = client.post(
        "/api/v1/users/login",
        {"email": "alice@example.com", "password": "secret-password"},
        format="json",
    )
    assert login.status_code == 200
    access_token = login.json()["token"]["access"]
    refresh_token = login.json()["token"]["refresh"]

    # 6. Profile without token -> 401 middleware-002
    unauth = client.get("/api/v1/users/profile")
    assert unauth.status_code == 401
    assert unauth.json()["trace_id"] == "middleware-002"

    # 7. Profile with Bearer token -> GET 200 UserEntity
    profile = client.get(
        "/api/v1/users/profile",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
    )
    assert profile.status_code == 200
    assert profile.json()["email"] == "alice@example.com"

    # 8. Refresh token -> 200 with rotated access token
    refreshed = client.post(
        "/api/v1/users/refresh-token",
        {"refresh_token": refresh_token},
        format="json",
    )
    assert refreshed.status_code == 200
    new_access = refreshed.json()["token"]["access"]
    new_refresh = refreshed.json()["token"]["refresh"]

    # 9. Logout -> 200 null, then profile with old/new access token fails 401
    logout = client.post(
        "/api/v1/users/logout",
        {"refresh_token": new_refresh},
        format="json",
    )
    assert logout.status_code == 200
    assert logout.json() is None

    after_logout = client.get(
        "/api/v1/users/profile",
        HTTP_AUTHORIZATION=f"Bearer {new_access}",
    )
    assert after_logout.status_code == 401
    assert after_logout.json()["trace_id"] == "middleware-002"

    # 10. Verify MongoDB Activity Logs recorded all auth events
    actions = [doc["action"] for doc in in_memory_mongo_collection.docs]
    assert actions == [
        "USER_REGISTER",
        "USER_LOGIN",
        "USER_LOGIN",
        "USER_REFRESH_TOKEN",
        "USER_LOGOUT",
    ]
