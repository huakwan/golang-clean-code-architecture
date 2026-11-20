from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from src.infrastructure.database.postgres.models import (
    UserModel,
    UserPermissionModel,
    UserTokenModel,
)
from src.shared.authentication.jwt_authentication import hash_token


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

    stored_token = UserTokenModel.objects.get(user_id=user_id)
    assert stored_token.access != access_token
    assert stored_token.access == hash_token(access_token)
    assert stored_token.refresh != refresh_token
    assert stored_token.refresh == hash_token(refresh_token)

    refresh_as_access = client.get(
        "/api/v1/users/profile",
        HTTP_AUTHORIZATION=f"Bearer {refresh_token}",
    )
    assert refresh_as_access.status_code == 401
    assert refresh_as_access.json()["trace_id"] == "middleware-002"

    access_as_refresh = client.post(
        "/api/v1/users/refresh-token",
        {"refresh_token": access_token},
        format="json",
    )
    assert access_as_refresh.status_code == 400
    assert access_as_refresh.json()["trace_id"] == "users-003"

    # 6. Profile without token -> 401 middleware-002
    unauth = client.get("/api/v1/users/profile")
    assert unauth.status_code == 401
    assert unauth.json()["trace_id"] == "middleware-002"

    # 7. Profile with Bearer token -> GET 200 UserEntity + permission
    profile = client.get(
        "/api/v1/users/profile",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
    )
    assert profile.status_code == 200
    assert profile.json()["email"] == "alice@example.com"
    assert profile.json()["permission"] == "user"

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


@pytest.mark.django_db
def test_register_and_login_normalize_email_case_and_prevent_duplicates(
    in_memory_mongo_collection,
) -> None:
    client = APIClient()

    reg = client.post(
        "/api/v1/users/register",
        {
            "email": "Alice@Example.COM",
            "password": "secret-password",
            "first_name": "Alice",
            "last_name": "Smith",
        },
        format="json",
    )
    assert reg.status_code == 201
    assert reg.json()["email"] == "alice@example.com"

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

    login = client.post(
        "/api/v1/users/login",
        {"email": "ALICE@EXAMPLE.COM", "password": "secret-password"},
        format="json",
    )
    assert login.status_code == 200


@pytest.mark.django_db
def test_auth_endpoints_enforce_rate_limiting_and_ignore_spoofed_xff(
    in_memory_mongo_collection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.infrastructure.django_app.throttling import ClientIPScopedRateThrottle

    monkeypatch.setitem(ClientIPScopedRateThrottle.THROTTLE_RATES, "auth_login", "2/min")
    client = APIClient()

    for _ in range(2):
        resp = client.post(
            "/api/v1/users/login",
            {"email": "nobody@example.com", "password": "wrong"},
            format="json",
        )
        assert resp.status_code == 400

    throttled = client.post(
        "/api/v1/users/login",
        {"email": "nobody@example.com", "password": "wrong"},
        format="json",
        HTTP_X_FORWARDED_FOR="9.9.9.9",
    )
    assert throttled.status_code == 429
    assert throttled.json()["trace_id"] == "middleware-004"
    assert "Retry-After" in throttled.headers


@pytest.mark.django_db
def test_user_endpoints_reject_null_non_string_and_oversized_fields(
    in_memory_mongo_collection,
) -> None:
    client = APIClient()

    bad_register_payloads = [
        {"email": "n@example.com", "password": None, "first_name": "A", "last_name": "B"},
        {"email": "n@example.com", "password": "pw", "first_name": None, "last_name": "B"},
        {"email": "n@example.com", "password": "pw", "first_name": "A", "last_name": None},
        {"email": "n@example.com", "password": 12345, "first_name": "A", "last_name": "B"},
        {"email": "n@example.com", "password": "pw", "first_name": "a" * 151, "last_name": "B"},
    ]
    for payload in bad_register_payloads:
        resp = client.post("/api/v1/users/register", payload, format="json")
        assert resp.status_code == 400
        assert resp.json()["trace_id"] == "users-001"
    assert not UserModel.objects.filter(email="n@example.com").exists()

    for payload in (
        {"email": None, "password": None},
        {"email": "a@b.com", "password": 123},
    ):
        resp = client.post("/api/v1/users/login", payload, format="json")
        assert resp.status_code == 400
        assert resp.json()["trace_id"] == "users-002"

    for endpoint, trace_id in (
        ("/api/v1/users/refresh-token", "users-003"),
        ("/api/v1/users/logout", "users-004"),
    ):
        for bad_tok in (123, ["tok"], None):
            resp = client.post(endpoint, {"refresh_token": bad_tok}, format="json")
            assert resp.status_code == 400
            assert resp.json()["trace_id"] == trace_id


@pytest.mark.django_db
def test_user_profile_returns_permission_without_duplicate_user_query(
    in_memory_mongo_collection,
    django_assert_num_queries,
) -> None:
    client = APIClient()
    client.post(
        "/api/v1/users/register",
        {
            "email": "prof@example.com",
            "password": "secret-password",
            "first_name": "Prof",
            "last_name": "User",
        },
        format="json",
    )
    login = client.post(
        "/api/v1/users/login",
        {"email": "prof@example.com", "password": "secret-password"},
        format="json",
    )
    access_token = login.json()["token"]["access"]

    with django_assert_num_queries(3):
        resp = client.get(
            "/api/v1/users/profile",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )
    assert resp.status_code == 200
    assert resp.json()["email"] == "prof@example.com"
    assert resp.json()["permission"] == "user"

    UserPermissionModel.objects.filter(user__email="prof@example.com").update(permission="admin")
    admin_resp = client.get(
        "/api/v1/users/profile",
        HTTP_AUTHORIZATION=f"Bearer {access_token}",
    )
    assert admin_resp.status_code == 200
    assert admin_resp.json()["permission"] == "admin"


@pytest.mark.django_db
def test_register_rolls_back_user_if_permission_creation_fails(
    in_memory_mongo_collection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from src.domain.entities.user import UserRegisterRequest
    from src.infrastructure.container import get_container
    from src.interfaces.repositories.postgres.user_repository import PostgresUserRepository

    def boom(self, user_id: int, permission: str):  # type: ignore[no-untyped-def]
        raise RuntimeError("permission insert failed")

    monkeypatch.setattr(PostgresUserRepository, "insert_user_permission", boom)

    with pytest.raises(RuntimeError, match="permission insert failed"):
        get_container().user_usecase.register_user(
            UserRegisterRequest("rollback@example.com", "secret-pw", "Roll", "Back")
        )

    assert not UserModel.objects.filter(email="rollback@example.com").exists()


@pytest.mark.django_db
def test_deleting_user_cascades_tokens_and_permissions_and_upsert_stays_unique(
    in_memory_mongo_collection,
) -> None:
    client = APIClient()
    reg = client.post(
        "/api/v1/users/register",
        {
            "email": "cascade@example.com",
            "password": "secret-password",
            "first_name": "Cascade",
            "last_name": "User",
        },
        format="json",
    )
    assert reg.status_code == 201
    user_id = reg.json()["id"]

    for _ in range(2):
        login = client.post(
            "/api/v1/users/login",
            {"email": "cascade@example.com", "password": "secret-password"},
            format="json",
        )
        assert login.status_code == 200

    assert UserTokenModel.objects.filter(user_id=user_id).count() == 1
    assert UserPermissionModel.objects.filter(user_id=user_id).count() == 1

    UserModel.objects.filter(id=user_id).delete()

    assert UserTokenModel.objects.filter(user_id=user_id).count() == 0
    assert UserTokenModel.objects.filter(user__isnull=True).count() == 0
    assert UserPermissionModel.objects.filter(user_id=user_id).count() == 0
    assert UserPermissionModel.objects.filter(user__isnull=True).count() == 0
