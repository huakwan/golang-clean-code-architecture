from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.domain.entities.crud import (
    DataListResponse,
    DataResponse,
    DatasourceType,
    EntityModelInfo,
    ICRUDDataModel,
)
from src.domain.exceptions import OperationNotAllowedError
from src.usecases.crud.crud_usecase import MAX_PAGE, CrudUsecase


class WritableModel(ICRUDDataModel):
    @classmethod
    def table_name(cls) -> str:
        return "users"

    @classmethod
    def datasource(cls) -> DatasourceType:
        return DatasourceType.POSTGRESQL


class AuditLogModel(ICRUDDataModel):
    @classmethod
    def table_name(cls) -> str:
        return "activity_logs"

    @classmethod
    def datasource(cls) -> DatasourceType:
        return DatasourceType.MONGODB

    @classmethod
    def allowed_operations(cls, permission: str | None = None) -> frozenset[str]:
        if permission == "admin":
            return frozenset({"read", "delete"})
        return frozenset({"read"})


class ReadOnlyTokenModel(ICRUDDataModel):
    @classmethod
    def table_name(cls) -> str:
        return "user_tokens"

    @classmethod
    def datasource(cls) -> DatasourceType:
        return DatasourceType.POSTGRESQL

    @classmethod
    def allowed_operations(cls, permission: str | None = None) -> frozenset[str]:
        return frozenset({"read"})


def _make_crud_usecase(model_cls: type[ICRUDDataModel]) -> tuple[CrudUsecase, MagicMock]:
    repo = MagicMock()
    uc = CrudUsecase(repo_factory=lambda slug: (model_cls, repo))
    return uc, repo


def test_crud_list_clamps_page_and_page_size() -> None:
    uc, repo = _make_crud_usecase(WritableModel)
    repo.get_list.return_value = DataListResponse(0, [], 1, 1000, 0, 0)

    uc.list_records("users", page=0, page_size=5000)
    repo.get_list.assert_called_once_with(page=1, page_size=1000, filters=None)

    repo.get_list.reset_mock()
    uc.list_records("users", page=2, page_size=0)
    repo.get_list.assert_called_once_with(page=2, page_size=10, filters=None)

    repo.get_list.reset_mock()
    uc.list_records("users", page=99_999_999_999_999_999_999, page_size=10)
    repo.get_list.assert_called_once_with(page=MAX_PAGE, page_size=10, filters=None)


def test_crud_writable_model_allows_all_operations() -> None:
    uc, repo = _make_crud_usecase(WritableModel)
    repo.describe_data_source.return_value = {"type": "record", "name": "users", "fields": []}
    repo.get_one_by_id.return_value = DataResponse(0, {"id": 1})
    repo.create.return_value = DataResponse(0, {"id": 2})
    repo.update.return_value = DataResponse(0, {"id": 2})

    assert uc.describe("users")["name"] == "users"
    assert uc.retrieve("users", "1").data["id"] == 1
    assert uc.create("users", {"email": "a@b.com"}).data["id"] == 2
    assert uc.update("users", "2", {"first_name": "Updated"}).data["id"] == 2
    uc.delete("users", "2")
    repo.delete.assert_called_once_with("2")


def test_crud_audit_log_model_is_read_only_for_user_and_deletable_by_admin() -> None:
    uc, repo = _make_crud_usecase(AuditLogModel)
    repo.describe_data_source.return_value = {
        "type": "record",
        "name": "activity-logs",
        "fields": [],
    }
    repo.get_list.return_value = DataListResponse(0, [], 1, 10, 0, 0)
    repo.get_one_by_id.return_value = DataResponse(0, {"id": "abc"})

    assert uc.describe("activity-logs", permission="user")["name"] == "activity-logs"
    assert uc.list_records("activity-logs", permission="user").total_data == 0
    assert uc.retrieve("activity-logs", "abc", permission="user").data["id"] == "abc"

    for perm in (None, "user"):
        with pytest.raises(OperationNotAllowedError, match="create"):
            uc.create("activity-logs", {"action": "FAKE"}, permission=perm)

        with pytest.raises(OperationNotAllowedError, match="update"):
            uc.update("activity-logs", "abc", {"action": "TAMPER"}, permission=perm)

        with pytest.raises(OperationNotAllowedError, match="delete"):
            uc.delete("activity-logs", "abc", permission=perm)

    repo.delete.assert_not_called()

    uc.delete("activity-logs", "abc", permission="admin")
    repo.delete.assert_called_once_with("abc")

    with pytest.raises(OperationNotAllowedError, match="create"):
        uc.create("activity-logs", {"action": "FAKE"}, permission="admin")

    with pytest.raises(OperationNotAllowedError, match="update"):
        uc.update("activity-logs", "abc", {"action": "TAMPER"}, permission="admin")


def test_crud_read_only_token_model_blocks_mutations_even_for_admin() -> None:
    uc, repo = _make_crud_usecase(ReadOnlyTokenModel)
    repo.describe_data_source.return_value = {
        "type": "record",
        "name": "user-tokens",
        "fields": [],
    }

    assert uc.describe("user-tokens", permission="admin")["name"] == "user-tokens"

    for perm in (None, "user", "admin"):
        with pytest.raises(OperationNotAllowedError, match="create"):
            uc.create("user-tokens", {"user_id": 1}, permission=perm)
        with pytest.raises(OperationNotAllowedError, match="update"):
            uc.update("user-tokens", "1", {"user_id": 1}, permission=perm)
        with pytest.raises(OperationNotAllowedError, match="delete"):
            uc.delete("user-tokens", "1", permission=perm)


def test_crud_usecase_list_models_delegates_to_model_lister() -> None:
    repo = MagicMock()
    expected = [
        EntityModelInfo(
            slug="activity-logs",
            label="Activity Logs",
            datasource="mongodb",
            allowed_operations=["read"],
        )
    ]
    lister = MagicMock(return_value=expected)
    uc = CrudUsecase(repo_factory=lambda slug: (WritableModel, repo), model_lister=lister)

    result = uc.list_models(permission="user")
    assert result == expected
    lister.assert_called_once_with("user")

    uc_without_lister = CrudUsecase(repo_factory=lambda slug: (WritableModel, repo))
    assert uc_without_lister.list_models(permission="admin") == []
