from __future__ import annotations

from src.domain.entities.crud import EntityModelInfo, ICRUDDataModel
from src.infrastructure.database.mongodb.models import ActivityLogDocument
from src.infrastructure.database.postgres.models import (
    UserModel,
    UserPermissionModel,
    UserTokenModel,
)
from src.shared.crud.converter import convert_name_to_crud_slug

REGISTERED_MODELS: tuple[type[ICRUDDataModel], ...] = (
    UserModel,
    UserTokenModel,
    UserPermissionModel,
    ActivityLogDocument,
)

_OPERATION_ORDER = ("read", "create", "update", "delete")


def get_crud_model_registry() -> dict[str, type[ICRUDDataModel]]:
    return {
        convert_name_to_crud_slug(model_cls.table_name()): model_cls
        for model_cls in REGISTERED_MODELS
    }


def list_registered_models(permission: str | None = None) -> list[EntityModelInfo]:
    items: list[EntityModelInfo] = []
    for model_cls in REGISTERED_MODELS:
        slug = convert_name_to_crud_slug(model_cls.table_name())
        label = model_cls.table_name().replace("_", " ").title()
        allowed = [op for op in _OPERATION_ORDER if op in model_cls.allowed_operations(permission)]
        items.append(
            EntityModelInfo(
                slug=slug,
                label=label,
                datasource=model_cls.datasource().value,
                allowed_operations=allowed,
            )
        )
    return items
