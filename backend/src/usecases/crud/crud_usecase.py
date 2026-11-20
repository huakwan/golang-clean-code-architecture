from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.domain.entities.crud import (
    DataListResponse,
    DataResponse,
    EntityModelInfo,
    ICRUDDataModel,
)
from src.domain.exceptions import OperationNotAllowedError
from src.domain.repositories.crud_repository import ICRUDRepository

RepoFactory = Callable[[str], tuple[type[ICRUDDataModel], ICRUDRepository]]
ModelLister = Callable[[str | None], list[EntityModelInfo]]

MAX_PAGE = 10_000
MAX_PAGE_SIZE = 1000
DEFAULT_PAGE_SIZE = 10


class CrudUsecase:
    """Application business logic for polyglot Dynamic CRUD operations."""

    def __init__(
        self,
        *,
        repo_factory: RepoFactory,
        model_lister: ModelLister | None = None,
    ) -> None:
        self._repo_factory = repo_factory
        self._model_lister = model_lister

    def list_models(self, *, permission: str | None = None) -> list[EntityModelInfo]:
        if self._model_lister is None:
            return []
        return self._model_lister(permission)

    def _resolve(
        self,
        slug: str,
        operation: str,
        *,
        permission: str | None = None,
    ) -> ICRUDRepository:
        model_cls, repo = self._repo_factory(slug)
        if operation not in model_cls.allowed_operations(permission):
            raise OperationNotAllowedError(f"Operation '{operation}' is not allowed on '{slug}'")
        return repo

    def describe(self, slug: str, *, permission: str | None = None) -> dict[str, Any]:
        repo = self._resolve(slug, "read", permission=permission)
        return repo.describe_data_source()

    def list_records(
        self,
        slug: str,
        *,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        filters: dict[str, Any] | None = None,
        permission: str | None = None,
    ) -> DataListResponse:
        repo = self._resolve(slug, "read", permission=permission)
        safe_page = min(max(1, page), MAX_PAGE)
        safe_page_size = DEFAULT_PAGE_SIZE if page_size <= 0 else min(page_size, MAX_PAGE_SIZE)
        return repo.get_list(page=safe_page, page_size=safe_page_size, filters=filters)

    def retrieve(
        self,
        slug: str,
        record_id: str,
        *,
        permission: str | None = None,
    ) -> DataResponse:
        repo = self._resolve(slug, "read", permission=permission)
        return repo.get_one_by_id(record_id)

    def create(
        self,
        slug: str,
        payload: dict[str, Any],
        *,
        permission: str | None = None,
    ) -> DataResponse:
        repo = self._resolve(slug, "create", permission=permission)
        return repo.create(payload)

    def update(
        self,
        slug: str,
        record_id: str,
        payload: dict[str, Any],
        *,
        permission: str | None = None,
    ) -> DataResponse:
        repo = self._resolve(slug, "update", permission=permission)
        return repo.update(record_id, payload)

    def delete(
        self,
        slug: str,
        record_id: str,
        *,
        permission: str | None = None,
    ) -> None:
        repo = self._resolve(slug, "delete", permission=permission)
        repo.delete(record_id)
