from __future__ import annotations

import pytest
from rest_framework.test import APIClient


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
    assert models_by_slug["activity-logs"]["datasource"] == "mongodb"
    assert models_by_slug["activity-logs"]["allowed_operations"] == ["read", "delete"]


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
def test_mongodb_activity_logs_enforces_read_and_delete_only(in_memory_mongo_collection) -> None:
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

    # Create is BLOCKED with 405
    blocked_create = client.post(
        "/api/v1/data/activity-logs/",
        {"action": "FORGED"},
        format="json",
        **auth,
    )
    assert blocked_create.status_code == 405
    assert blocked_create.json()["trace_id"] == "crud-405"

    # Update is BLOCKED with 405
    blocked_update = client.put(
        f"/api/v1/data/activity-logs/{first_id}",
        {"action": "TAMPERED"},
        format="json",
        **auth,
    )
    assert blocked_update.status_code == 405
    assert blocked_update.json()["trace_id"] == "crud-405"

    # Delete IS allowed -> 204
    deleted = client.delete(f"/api/v1/data/activity-logs/{first_id}", **auth)
    assert deleted.status_code == 204
    assert client.get("/api/v1/data/activity-logs/", **auth).json()["total_data"] == 1
