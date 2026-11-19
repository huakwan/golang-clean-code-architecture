from __future__ import annotations

import ast
from pathlib import Path

import pytest

from src.domain.entities.crud import (
    ALL_CRUD_OPERATIONS,
    DataListResponse,
    DataResponse,
    DatasourceType,
    ICRUDDataModel,
)
from src.domain.entities.monitor import MonitorEntity
from src.domain.entities.user import (
    UserEntity,
    UserLoginResponse,
    UserRegisterRequest,
    UserTokenEntity,
)


def test_domain_layer_has_zero_framework_imports() -> None:
    domain_root = Path(__file__).resolve().parents[3] / "domain"
    forbidden = {"django", "rest_framework", "pymongo", "bson"}
    for py_file in domain_root.rglob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] not in forbidden, (
                        f"Forbidden import '{alias.name}' in {py_file}"
                    )
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] not in forbidden, (
                    f"Forbidden import '{node.module}' in {py_file}"
                )


@pytest.mark.parametrize(
    "email",
    [
        "user@example.com",
        "john.doe@sub.domain.org",
        "first-last_1@company.io",
    ],
)
def test_register_request_valid_emails(email: str) -> None:
    req = UserRegisterRequest(
        email=email,
        password="secret",
        first_name="Jane",
        last_name="Doe",
    )
    assert req.is_valid_email() is True


@pytest.mark.parametrize(
    "email",
    [
        "",
        "plainaddress",
        "@missinguser.com",
        "user@",
        "user@domain",
        "user@domain.toolongtld",
    ],
)
def test_register_request_invalid_emails(email: str) -> None:
    req = UserRegisterRequest(
        email=email,
        password="secret",
        first_name="Jane",
        last_name="Doe",
    )
    assert req.is_valid_email() is False


def test_user_entity_and_login_response_serialization() -> None:
    user = UserEntity(
        id=1,
        email="jane@example.com",
        first_name="Jane",
        last_name="Doe",
        created_at="2026-01-01T00:00:00Z",
        updated_at="2026-01-01T00:00:00Z",
    )
    token = UserTokenEntity(access="acc", refresh="ref")
    login_resp = UserLoginResponse(user=user, token=token)

    data = login_resp.to_dict()
    assert data["user"]["email"] == "jane@example.com"
    assert "password" not in data["user"]
    assert data["token"] == {"access": "acc", "refresh": "ref"}


def test_monitor_entity_serialization() -> None:
    monitor = MonitorEntity(name="PYTHON DJANGO CLEAN API", version="0.0.1")
    assert monitor.to_dict() == {"name": "PYTHON DJANGO CLEAN API", "version": "0.0.1"}


def test_crud_data_model_default_allowed_operations() -> None:
    class SampleModel(ICRUDDataModel):
        @classmethod
        def table_name(cls) -> str:
            return "samples"

        @classmethod
        def datasource(cls) -> DatasourceType:
            return DatasourceType.POSTGRESQL

    assert SampleModel.allowed_operations() == ALL_CRUD_OPERATIONS
    assert set(SampleModel.allowed_operations()) == {"read", "create", "update", "delete"}


def test_data_list_response_serialization() -> None:
    resp = DataListResponse(
        code=0,
        data=[{"id": 1}],
        page=1,
        page_size=10,
        total_page=1,
        total_data=1,
        message="",
        data_schema={"type": "record", "name": "users", "fields": []},
    )
    d = resp.to_dict()
    assert d["total_data"] == 1
    assert d["total_page"] == 1
    assert d["page_size"] == 10
    assert d["data_schema"]["name"] == "users"

    single = DataResponse(code=0, data={"id": 1}, message="", data_schema=None)
    assert single.to_dict() == {"code": 0, "data": {"id": 1}, "message": "", "data_schema": None}
