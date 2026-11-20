from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from django.conf import settings
from django.test import override_settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from src.domain.entities.user import UserEntity, UserPermissionEntity
from src.domain.exceptions import (
    ConflictError,
    DatabaseError,
    DomainError,
    NotFoundError,
    OperationNotAllowedError,
    ValidationError,
)
from src.infrastructure.django_app.authentication import CustomJWTAuthentication
from src.interfaces.handlers.django.entities.filter import get_client_ip
from src.interfaces.handlers.django.entities.response import custom_exception_handler


class _BareProtectedView(APIView):
    def get(self, request):  # type: ignore[no-untyped-def]
        return Response({"ok": True})


def test_get_client_ip_ignores_spoofed_xff_when_no_trusted_proxies() -> None:
    factory = APIRequestFactory()
    request = factory.get(
        "/api/v1/users/login",
        REMOTE_ADDR="203.0.113.5",
        HTTP_X_FORWARDED_FOR="1.2.3.4",
    )
    assert get_client_ip(request, trusted_proxies=()) == "203.0.113.5"


def test_get_client_ip_ignores_xff_from_untrusted_remote_addr() -> None:
    factory = APIRequestFactory()
    request = factory.get(
        "/api/v1/users/login",
        REMOTE_ADDR="203.0.113.9",
        HTTP_X_FORWARDED_FOR="1.2.3.4, 198.51.100.7",
    )
    assert get_client_ip(request, trusted_proxies=("10.0.0.0/8",)) == "203.0.113.9"


def test_get_client_ip_extracts_rightmost_untrusted_ip_from_trusted_proxy() -> None:
    factory = APIRequestFactory()
    request = factory.get(
        "/api/v1/users/login",
        REMOTE_ADDR="10.0.0.1",
        HTTP_X_FORWARDED_FOR="1.2.3.4, 198.51.100.7",
    )
    assert get_client_ip(request, trusted_proxies=("10.0.0.0/8",)) == "198.51.100.7"


def test_get_client_ip_walks_trusted_proxy_chain_right_to_left() -> None:
    factory = APIRequestFactory()
    request = factory.get(
        "/api/v1/users/login",
        REMOTE_ADDR="10.0.0.1",
        HTTP_X_FORWARDED_FOR="1.2.3.4, 198.51.100.7, 10.0.0.2",
    )
    assert get_client_ip(request, trusted_proxies=("10.0.0.0/8",)) == "198.51.100.7"


def test_get_client_ip_handles_invalid_ips_gracefully() -> None:
    factory = APIRequestFactory()
    request = factory.get(
        "/api/v1/users/login",
        REMOTE_ADDR="not-an-ip",
        HTTP_X_FORWARDED_FOR="1.2.3.4",
    )
    assert get_client_ip(request, trusted_proxies=("10.0.0.0/8", "bad-cidr")) == "not-an-ip"


def test_drf_defaults_are_fail_closed_for_unauthenticated_views() -> None:
    assert settings.REST_FRAMEWORK["DEFAULT_PERMISSION_CLASSES"] == [
        "rest_framework.permissions.IsAuthenticated",
    ]
    assert settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"] == [
        "src.infrastructure.django_app.authentication.CustomJWTAuthentication",
    ]

    factory = APIRequestFactory()
    request = factory.get("/bare-protected")
    response = _BareProtectedView.as_view()(request)
    assert response.status_code == 401
    assert response.data["trace_id"] == "middleware-002"


def test_interfaces_handlers_and_crud_factory_have_no_outer_layer_imports() -> None:
    src_root = Path(__file__).resolve().parents[3]
    targets = list((src_root / "interfaces" / "handlers").rglob("*.py"))
    targets.append(src_root / "interfaces" / "repositories" / "crud" / "factory.py")
    forbidden_prefixes = ("src.infrastructure", "src.config")

    for py_file in targets:
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith(forbidden_prefixes), (
                        f"Outer-layer import '{alias.name}' in {py_file}"
                    )
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith(forbidden_prefixes), (
                    f"Outer-layer import '{node.module}' in {py_file}"
                )


def test_custom_jwt_authentication_strips_bearer_once_and_validates_format() -> None:
    user_usecase = MagicMock()
    entity = UserEntity(1, "a@b.com", "A", "B", "", "")
    perm = UserPermissionEntity(1, 1, "user")
    user_usecase.authenticate.return_value = (entity, perm)

    auth = CustomJWTAuthentication(user_usecase=user_usecase)
    factory = APIRequestFactory()

    valid_req = factory.get("/api/v1/users/profile", HTTP_AUTHORIZATION="Bearer raw.jwt.token")
    result = auth.authenticate(valid_req)  # type: ignore[arg-type]
    assert result is not None
    authenticated_user, token = result
    assert authenticated_user.entity == entity
    assert authenticated_user.permission == perm
    assert token == "raw.jwt.token"
    user_usecase.authenticate.assert_called_once_with("raw.jwt.token")

    for bad_header in ("Token raw.jwt.token", "Bearer   "):
        bad_req = factory.get("/api/v1/users/profile", HTTP_AUTHORIZATION=bad_header)
        with pytest.raises(AuthenticationFailed, match="token format is invalid"):
            auth.authenticate(bad_req)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("exc", "expected_status", "expected_trace_id"),
    [
        (OperationNotAllowedError("disallowed"), 405, "crud-405"),
        (NotFoundError("missing"), 404, "error"),
        (ConflictError("duplicate"), 409, "error"),
        (ValidationError("bad input"), 400, "error"),
        (DatabaseError("db down"), 503, "crud-503"),
        (DomainError("generic domain"), 500, "error"),
    ],
)
def test_custom_exception_handler_maps_domain_errors(
    exc: DomainError,
    expected_status: int,
    expected_trace_id: str,
) -> None:
    resp = custom_exception_handler(exc, {})
    assert resp is not None
    assert resp.status_code == expected_status
    assert resp.data["trace_id"] == expected_trace_id


def test_custom_exception_handler_hides_unhandled_500_when_debug_false() -> None:
    with override_settings(DEBUG=False):
        resp = custom_exception_handler(RuntimeError("secret details"), {})
        assert resp is not None
        assert resp.status_code == 500
        assert resp.data == {"trace_id": "error", "message": "internal server error"}

    with override_settings(DEBUG=True):
        assert custom_exception_handler(RuntimeError("secret details"), {}) is None


def test_request_logger_middleware_handles_request_id_and_logs_exceptions(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import logging
    import re

    from django.http import HttpResponse
    from django.test import RequestFactory

    from src.infrastructure.django_app.middlewares import RequestLoggerMiddleware

    monkeypatch.setattr(logging.getLogger("api.request"), "propagate", True)
    rf = RequestFactory()

    mw = RequestLoggerMiddleware(lambda _req: HttpResponse("ok", status=200))
    req_auto = rf.get("/api/v1/")
    resp_auto = mw(req_auto)
    assert re.fullmatch(r"[0-9a-f]{32}", resp_auto["X-Request-ID"])
    assert getattr(req_auto, "request_id", None) == resp_auto["X-Request-ID"]

    req_valid = rf.get("/api/v1/", HTTP_X_REQUEST_ID="req-abc_123.4")
    resp_valid = mw(req_valid)
    assert resp_valid["X-Request-ID"] == "req-abc_123.4"

    req_unsafe = rf.get("/api/v1/", HTTP_X_REQUEST_ID="bad\nid with spaces")
    resp_unsafe = mw(req_unsafe)
    assert resp_unsafe["X-Request-ID"] != "bad\nid with spaces"
    assert re.fullmatch(r"[0-9a-f]{32}", resp_unsafe["X-Request-ID"])

    def failing_view(_req):  # type: ignore[no-untyped-def]
        raise RuntimeError("boom")

    failing_mw = RequestLoggerMiddleware(failing_view)
    req_err = rf.get("/api/v1/fail", HTTP_X_REQUEST_ID="trace-err-1")
    with caplog.at_level(logging.ERROR, logger="api.request"), pytest.raises(RuntimeError):
        failing_mw(req_err)
    assert any("trace-err-1" in rec.message and "500" in rec.message for rec in caplog.records)


def test_postgres_crud_parse_pk_supports_int_and_uuid_pks() -> None:
    import uuid
    from types import SimpleNamespace

    from django.db import models

    from src.infrastructure.database.postgres.models import UserModel
    from src.interfaces.repositories.postgres.crud_repository import PostgresCRUDRepository

    int_repo = PostgresCRUDRepository(UserModel)
    assert int_repo._parse_pk("42") == 42
    with pytest.raises(ValidationError):
        int_repo._parse_pk("not-int")

    uuid_pk = models.UUIDField(primary_key=True)

    class _FakeUUIDModel:
        _meta = SimpleNamespace(pk=uuid_pk)

    uuid_repo = PostgresCRUDRepository(_FakeUUIDModel)  # type: ignore[arg-type]
    sample_uuid = str(uuid.uuid4())
    parsed = uuid_repo._parse_pk(sample_uuid)
    assert isinstance(parsed, uuid.UUID)
    assert str(parsed) == sample_uuid
    with pytest.raises(ValidationError):
        uuid_repo._parse_pk("not-a-uuid")


def test_in_memory_mongo_collection_satisfies_protocol() -> None:
    from src.interfaces.repositories.mongodb.collection import MongoCollectionProtocol
    from src.tests.conftest import InMemoryMongoCollection

    assert isinstance(InMemoryMongoCollection(), MongoCollectionProtocol)
