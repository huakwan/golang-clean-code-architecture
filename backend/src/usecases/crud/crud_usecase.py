from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.domain.entities.crud import DataListResponse, DataResponse, ICRUDDataModel
from src.domain.exceptions import OperationNotAllowedError
from src.domain.repositories.crud_repository import ICRUDRepository

RepoFactory = Callable[[str], tuple[type[ICRUDDataModel], ICRUDRepository]]

MAX_PAGE_SIZE = 1000
DEFAULT_PAGE_SIZE = 10


class CrudUsecase:
    """Application business logic for polyglot Dynamic CRUD operations."""

    def __init__(self, *, repo_factory: RepoFactory) -> None:
        self._repo_factory = repo_factory

    def _resolve(self, slug: str, operation: str) -> ICRUDRepository:
        model_cls, repo = self._repo_factory(slug)
        if operation not in model_cls.allowed_operations():
            raise OperationNotAllowedError(
                f"Operation '{operation}' is not allowed on '{slug}'"
            )
        return repo

    def describe(self, slug: str) -> dict[str, Any]:
        repo = self._resolve(slug, "read")
        return repo.describe_data_source()

    def list_records(
        self,
        slug: str,
        *,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        filters: dict[str, Any] | None = None,
    ) -> DataListResponse:
        repo = self._resolve(slug, "read")
        safe_page = max(1, page)
        safe_page_size = DEFAULT_PAGE_SIZE if page_size <= 0 else min(page_size, MAX_PAGE_SIZE)
        return repo.get_list(page=safe_page, page_size=safe_page_size, filters=filters)

    def retrieve(self, slug: str, record_id: str) -> DataResponse:
        repo = self._resolve(slug, "read")
        return repo.get_one_by_id(record_id)

    def create(self, slug: str, payload: dict[str, Any]) -> DataResponse:
        repo = self._resolve(slug, "create")
        return repo.create(payload)

    def update(self, slug: str, record_id: str, payload: dict[str, Any]) -> DataResponse:
        repo = self._resolve(slug, "update")
        return repo.update(record_id, payload)

    def delete(self, slug: str, record_id: str) -> None:
        repo = self._resolve(slug, "delete")
        repo.delete(record_id)
