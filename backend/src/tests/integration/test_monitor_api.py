from __future__ import annotations

from rest_framework.test import APIClient


def test_monitor_health_check_returns_name_and_version() -> None:
    client = APIClient()
    resp = client.get("/api/v1/")
    assert resp.status_code == 200
    body = resp.json()
    assert "name" in body
    assert "version" in body


def test_unknown_route_returns_json_404_middleware_001() -> None:
    client = APIClient()
    resp = client.get("/api/v1/does-not-exist")
    assert resp.status_code == 404
    assert resp.json() == {"trace_id": "middleware-001", "message": "router not found"}


def test_swagger_ui_and_openapi_schema_are_accessible() -> None:
    client = APIClient()
    schema_resp = client.get("/api/schema/")
    assert schema_resp.status_code == 200
    swagger_resp = client.get("/swagger/")
    assert swagger_resp.status_code == 200
