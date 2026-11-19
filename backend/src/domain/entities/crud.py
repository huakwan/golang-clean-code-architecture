from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class DatasourceType(StrEnum):
    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"


ALL_CRUD_OPERATIONS: frozenset[str] = frozenset({"read", "create", "update", "delete"})


class ICRUDDataModel(ABC):
    """Contract implemented by every model registered in the Dynamic CRUD engine."""

    @classmethod
    @abstractmethod
    def table_name(cls) -> str:
        """Return the underlying table or collection name."""

    @classmethod
    @abstractmethod
    def datasource(cls) -> DatasourceType:
        """Return the datasource backing this model."""

    @classmethod
    def allowed_operations(cls) -> frozenset[str]:
        """Return allowed CRUD operations ('read', 'create', 'update', 'delete')."""
        return ALL_CRUD_OPERATIONS


@dataclass(frozen=True)
class EntityModelInfo:
    slug: str
    label: str
    datasource: str
    allowed_operations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DataResponse:
    code: int
    data: Any
    message: str = ""
    data_schema: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DataListResponse:
    code: int
    data: list[dict[str, Any]]
    page: int
    page_size: int
    total_page: int
    total_data: int
    message: str = ""
    data_schema: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
