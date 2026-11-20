from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.domain.entities.crud import (
    ADMIN_PERMISSION,
    READ_ONLY_CRUD_OPERATIONS,
    DatasourceType,
    ICRUDDataModel,
)


@dataclass(frozen=True)
class ActivityLogDocument(ICRUDDataModel):
    """Immutable audit trail document stored in MongoDB (auto-logged by auth events)."""

    id: str = ""
    user_id: int | None = None
    action: str = ""
    resource: str = ""
    status: str = ""
    ip_address: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None

    @classmethod
    def table_name(cls) -> str:
        return "activity_logs"

    @classmethod
    def datasource(cls) -> DatasourceType:
        return DatasourceType.MONGODB

    @classmethod
    def allowed_operations(cls, permission: str | None = None) -> frozenset[str]:
        if permission == ADMIN_PERMISSION:
            return frozenset({"read", "delete"})
        return READ_ONLY_CRUD_OPERATIONS
