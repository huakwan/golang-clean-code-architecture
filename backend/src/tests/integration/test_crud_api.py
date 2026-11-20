from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pymongo.errors import PyMongoError
from rest_framework.test import APIClient

from src.infrastructure.database.postgres.models import UserPermissionModel


def _register_and_login(client: APIClient, email: str = "admin@example.com") -> str:
    client.post(
        "/api/v1/users/register",
        {
            "email": email,
            "password": "password123",
            "first_name": "Admin",
            "last_name": "User",
        },
        format="json",
    )
    login = client.post(
        "/api/v1/users/login",
        {"email": email, "password": "password123"},
        format="json",
    )
    return str(login.json()["token"]["access"])


@pytest.mark.django_db
def test_crud_models_discovery_includes_allowed_operations(in_memory_mongo_collection) -> None:
    client = APIClient()
    token = _register_and_login(client)
    auth = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    resp = client.get("/api/v1/data/models/", **auth)
    assert resp.status_code == 200
    models_by_slug = {m["slug"]: m for m in resp.json()}

    assert set(models_by_slug.keys()) == {
        "users",
        "user-tokens",
        "user-permissions",
        "activity-logs",
    }
    assert models_by_slug["users"]["datasource"] == "postgresql"
    assert models_by_slug["users"]["allowed_operations"] == ["read", "create", "update", "delete"]
    assert models_by_slug["user-tokens"]["allowed_operations"] == ["read"]
    assert models_by_slug["activity-logs"]["datasource"] == "mongodb"
    assert models_by_slug["activity-logs"]["allowed_operations"] == ["read"]

    UserPermissionModel.objects.filter(user__email="admin@example.com").update(permission="admin")
    admin_resp = client.get("/api/v1/data/models/", **auth)
    assert admin_resp.status_code == 200
    admin_models = {m["slug"]: m for m in admin_resp.json()}
    assert admin_models["user-tokens"]["allowed_operations"] == ["read"]
    assert admin_models["activity-logs"]["allowed_operations"] == ["read", "delete"]


@pytest.mark.django_db
def test_postgres_crud_full_lifecycle_and_accurate_pagination(in_memory_mongo_collection) -> None:
    client = APIClient()
    token = _register_and_login(client)
    auth = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    # Describe
    desc = client.get("/api/v1/data/users/describe", **auth)
    assert desc.status_code == 200
    assert desc.json()["name"] == "users"
    assert "password" not in {f["name"] for f in desc.json()["fields"]}

    # Create two more users via Dynamic CRUD
    c1 = client.post(
        "/api/v1/data/users/",
        {
            "email": "u1@example.com",
            "password": "pw1",
            "first_name": "One",
            "last_name": "User",
        },
        format="json",
        **auth,
    )
    assert c1.status_code == 201
    created_id = c1.json()["data"]["id"]
    assert "password" not in c1.json()["data"]

    c2 = client.post(
        "/api/v1/data/users/",
        {
            "email": "u2@example.com",
            "password": "pw2",
            "first_name": "Two",
            "last_name": "User",
        },
        format="json",
        **auth,
    )
    assert c2.status_code == 201

    # List with _pageSize=2 when 3 total rows exist -> total_data=3, total_page=2 (Go bug fixed!)
    listing = client.get("/api/v1/data/users/?_page=1&_pageSize=2", **auth)
    assert listing.status_code == 200
    body = listing.json()
    assert len(body["data"]) == 2
    assert body["total_data"] == 3
    assert body["total_page"] == 2
    assert body["data_schema"]["name"] == "users"

    # Retrieve
    detail = client.get(f"/api/v1/data/users/{created_id}", **auth)
    assert detail.status_code == 200
    assert detail.json()["data"]["email"] == "u1@example.com"

    # Update with blank password must NOT overwrite existing password hash
    updated = client.put(
        f"/api/v1/data/users/{created_id}",
        {"first_name": "UpdatedOne", "password": ""},
        format="json",
        **auth,
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["first_name"] == "UpdatedOne"
    still_logs_in = client.post(
        "/api/v1/users/login",
        {"email": "u1@example.com", "password": "pw1"},
        format="json",
    )
    assert still_logs_in.status_code == 200

    # Invalid filter param returns 400 instead of 500
    bad_filter = client.get("/api/v1/data/users/?id=not-an-int", **auth)
    assert bad_filter.status_code == 400

    # Duplicate unique email returns 409 with generic domain message (no raw SQL)
    dup_create = client.post(
        "/api/v1/data/users/",
        {
            "email": "u1@example.com",
            "password": "pw1",
            "first_name": "Dup",
            "last_name": "User",
        },
        format="json",
        **auth,
    )
    assert dup_create.status_code == 409
    assert "UNIQUE constraint" not in dup_create.json()["message"]

    # Delete
    deleted = client.delete(f"/api/v1/data/users/{created_id}", **auth)
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/data/users/{created_id}", **auth).status_code == 404


@pytest.mark.django_db
def test_user_tokens_is_read_only_and_hides_sensitive_fields(in_memory_mongo_collection) -> None:
    client = APIClient()
    token = _register_and_login(client, email="tokens@example.com")
    auth = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    desc = client.get("/api/v1/data/user-tokens/describe", **auth)
    assert desc.status_code == 200
    field_names = {f["name"] for f in desc.json()["fields"]}
    assert "access" not in field_names
    assert "refresh" not in field_names

    listing = client.get("/api/v1/data/user-tokens/?_page=1&_pageSize=10", **auth)
    assert listing.status_code == 200
    assert listing.json()["total_data"] == 1
    row = listing.json()["data"][0]
    assert "access" not in row
    assert "refresh" not in row
    token_id = row["id"]

    detail = client.get(f"/api/v1/data/user-tokens/{token_id}", **auth)
    assert detail.status_code == 200
    assert "access" not in detail.json()["data"]
    assert "refresh" not in detail.json()["data"]

    for _role in ("user", "admin"):
        if _role == "admin":
            UserPermissionModel.objects.filter(user__email="tokens@example.com").update(
                permission="admin"
            )

        blocked_create = client.post(
            "/api/v1/data/user-tokens/",
            {"user_id": row["user_id"], "access": "x", "refresh": "y"},
            format="json",
            **auth,
        )
        assert blocked_create.status_code == 405
        assert blocked_create.json()["trace_id"] == "crud-405"

        blocked_update = client.put(
            f"/api/v1/data/user-tokens/{token_id}",
            {"access": "tampered"},
            format="json",
            **auth,
        )
        assert blocked_update.status_code == 405
        assert blocked_update.json()["trace_id"] == "crud-405"

        blocked_delete = client.delete(f"/api/v1/data/user-tokens/{token_id}", **auth)
        assert blocked_delete.status_code == 405
        assert blocked_delete.json()["trace_id"] == "crud-405"


@pytest.mark.django_db
def test_mongodb_activity_logs_is_read_only_for_user_and_deletable_by_admin(
    in_memory_mongo_collection,
) -> None:
    client = APIClient()
    token = _register_and_login(client)
    auth = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    # Describe activity-logs
    desc = client.get("/api/v1/data/activity-logs/describe", **auth)
    assert desc.status_code == 200
    assert desc.json()["name"] == "activity-logs"

    # List auto-logged auth events (USER_REGISTER + USER_LOGIN)
    listing = client.get("/api/v1/data/activity-logs/?_page=1&_pageSize=10", **auth)
    assert listing.status_code == 200
    assert listing.json()["total_data"] == 2
    first_id = listing.json()["data"][0]["id"]

    # Retrieve single log
    detail = client.get(f"/api/v1/data/activity-logs/{first_id}", **auth)
    assert detail.status_code == 200
    assert detail.json()["data"]["id"] == first_id

    # Regular user: create, update, and delete are ALL blocked with 405
    blocked_create = client.post(
        "/api/v1/data/activity-logs/",
        {"action": "FORGED"},
        format="json",
        **auth,
    )
    assert blocked_create.status_code == 405
    assert blocked_create.json()["trace_id"] == "crud-405"

    blocked_update = client.put(
        f"/api/v1/data/activity-logs/{first_id}",
        {"action": "TAMPERED"},
        format="json",
        **auth,
    )
    assert blocked_update.status_code == 405
    assert blocked_update.json()["trace_id"] == "crud-405"

    blocked_delete = client.delete(f"/api/v1/data/activity-logs/{first_id}", **auth)
    assert blocked_delete.status_code == 405
    assert blocked_delete.json()["trace_id"] == "crud-405"

    # Elevate user to admin: create and update stay blocked, delete IS allowed -> 204
    UserPermissionModel.objects.filter(user__email="admin@example.com").update(permission="admin")

    still_blocked_create = client.post(
        "/api/v1/data/activity-logs/",
        {"action": "FORGED"},
        format="json",
        **auth,
    )
    assert still_blocked_create.status_code == 405

    still_blocked_update = client.put(
        f"/api/v1/data/activity-logs/{first_id}",
        {"action": "TAMPERED"},
        format="json",
        **auth,
    )
    assert still_blocked_update.status_code == 405

    deleted = client.delete(f"/api/v1/data/activity-logs/{first_id}", **auth)
    assert deleted.status_code == 204
    assert client.get("/api/v1/data/activity-logs/", **auth).json()["total_data"] == 1


@pytest.mark.django_db
def test_mongodb_activity_logs_filtering_and_error_translation(
    in_memory_mongo_collection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = APIClient()
    token = _register_and_login(client, email="filter@example.com")
    auth = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    for bad_query in ("?$where=1", "?metadata.email=a", "?foo=bar", "?user_id=not-an-int"):
        resp = client.get(f"/api/v1/data/activity-logs/{bad_query}", **auth)
        assert resp.status_code == 400

    valid_action = client.get("/api/v1/data/activity-logs/?action=USER_LOGIN", **auth)
    assert valid_action.status_code == 200
    assert valid_action.json()["total_data"] == 1
    user_id = valid_action.json()["data"][0]["user_id"]

    valid_user = client.get(f"/api/v1/data/activity-logs/?user_id={user_id}", **auth)
    assert valid_user.status_code == 200
    assert valid_user.json()["total_data"] == 2

    monkeypatch.setattr(
        in_memory_mongo_collection,
        "count_documents",
        MagicMock(side_effect=PyMongoError("mongodb://secret-host:27017 connection error")),
    )
    unavailable = client.get("/api/v1/data/activity-logs/", **auth)
    assert unavailable.status_code == 503
    assert unavailable.json()["trace_id"] == "crud-503"
    assert "secret-host" not in unavailable.json()["message"]


@pytest.mark.django_db
def test_postgres_crud_enforces_required_password_model_validation_and_page_cap(
    in_memory_mongo_collection,
) -> None:
    client = APIClient()
    token = _register_and_login(client, email="crudval@example.com")
    auth = {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    missing_pw = client.post(
        "/api/v1/data/users/",
        {"email": "nopw@example.com", "first_name": "No", "last_name": "Pw"},
        format="json",
        **auth,
    )
    assert missing_pw.status_code == 400

    bad_email = client.post(
        "/api/v1/data/users/",
        {
            "email": "not-an-email",
            "password": "pw1",
            "first_name": "Bad",
            "last_name": "Email",
        },
        format="json",
        **auth,
    )
    assert bad_email.status_code == 400

    blank_first = client.post(
        "/api/v1/data/users/",
        {
            "email": "blank@example.com",
            "password": "pw1",
            "first_name": "",
            "last_name": "User",
        },
        format="json",
        **auth,
    )
    assert blank_first.status_code == 400

    too_long_first = client.post(
        "/api/v1/data/users/",
        {
            "email": "long@example.com",
            "password": "pw1",
            "first_name": "x" * 151,
            "last_name": "User",
        },
        format="json",
        **auth,
    )
    assert too_long_first.status_code == 400

    created = client.post(
        "/api/v1/data/users/",
        {
            "email": "valid@example.com",
            "password": "pw1",
            "first_name": "Valid",
            "last_name": "User",
        },
        format="json",
        **auth,
    )
    assert created.status_code == 201
    created_id = created.json()["data"]["id"]

    for empty_payload in ({}, {"unknown": "x"}, {"password": ""}):
        empty_put = client.put(
            f"/api/v1/data/users/{created_id}",
            empty_payload,
            format="json",
            **auth,
        )
        assert empty_put.status_code == 400
        assert "No updatable fields provided" in empty_put.json()["message"]

    bad_put_email = client.put(
        f"/api/v1/data/users/{created_id}",
        {"email": "bad-email"},
        format="json",
        **auth,
    )
    assert bad_put_email.status_code == 400

    for slug in ("users", "activity-logs"):
        huge_page = client.get(
            f"/api/v1/data/{slug}/?_page=99999999999999999999&_pageSize=10",
            **auth,
        )
        assert huge_page.status_code == 200
        assert huge_page.json()["page"] == 10_000
        assert huge_page.json()["data"] == []
