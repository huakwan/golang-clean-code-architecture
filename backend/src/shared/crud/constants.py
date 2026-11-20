from __future__ import annotations

from src.domain.entities.crud import ALL_CRUD_OPERATIONS, DatasourceType

SENSITIVE_FIELD_NAMES: frozenset[str] = frozenset({"password", "access", "refresh"})

__all__ = [
    "ALL_CRUD_OPERATIONS",
    "DatasourceType",
    "SENSITIVE_FIELD_NAMES",
]
