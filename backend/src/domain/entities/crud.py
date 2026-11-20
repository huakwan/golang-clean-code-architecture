from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable


class DatasourceType(StrEnum):
    POSTGRESQL = "postgresql"
    MONGODB = "mongodb"


ALL_CRUD_OPERATIONS: frozenset[str] = frozenset({"read", "create", "update", "delete"})
READ_ONLY_CRUD_OPERATIONS: frozenset[str] = frozenset({"read"})
ADMIN_PERMISSION = "admin"


@runtime_checkable
class ICRUDDataModel(Protocol):
    """Contract implemented by every model registered in the Dynamic CRUD engine."""

    @classmethod
    def table_name(cls) -> str:
        """Return the underlying table or collection name."""
        ...

    @classmethod
    def datasource(cls) -> DatasourceType:
        """Return the datasource backing this model."""
        ...

    @classmethod
    def allowed_operations(cls, permission: str | None = None) -> frozenset[str]:
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
