from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.domain.entities.crud import DataListResponse, DataResponse, DatasourceType, ICRUDDataModel
from src.domain.exceptions import OperationNotAllowedError
from src.usecases.crud.crud_usecase import CrudUsecase


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
    def allowed_operations(cls) -> frozenset[str]:
        return frozenset({"read", "delete"})


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


def test_crud_audit_log_model_blocks_create_and_update_but_allows_read_and_delete() -> None:
    uc, repo = _make_crud_usecase(AuditLogModel)
    repo.describe_data_source.return_value = {
        "type": "record",
        "name": "activity-logs",
        "fields": [],
    }

    assert uc.describe("activity-logs")["name"] == "activity-logs"
    uc.delete("activity-logs", "abc")
    repo.delete.assert_called_once_with("abc")

    with pytest.raises(OperationNotAllowedError, match="create"):
        uc.create("activity-logs", {"action": "FAKE"})

    with pytest.raises(OperationNotAllowedError, match="update"):
        uc.update("activity-logs", "abc", {"action": "TAMPER"})
