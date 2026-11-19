from __future__ import annotations

from collections.abc import Callable
from typing import Any

from src.config.crud_models import get_crud_model_registry
from src.domain.entities.crud import DatasourceType, ICRUDDataModel
from src.domain.exceptions import NotFoundError, ValidationError
from src.domain.repositories.crud_repository import ICRUDRepository
from src.infrastructure.database.mongodb.connector import MongoDBConnector
from src.interfaces.repositories.mongodb.crud_repository import MongoCRUDRepository
from src.interfaces.repositories.postgres.crud_repository import PostgresCRUDRepository


def get_crud_repository(
    slug: str,
    *,
    mongo_collection_provider: Callable[[str], Any] | None = None,
) -> tuple[type[ICRUDDataModel], ICRUDRepository]:
    """Resolve an entity slug to its registered model class and datasource repository."""
    registry = get_crud_model_registry()
    model_cls: type[Any] | None = registry.get(slug)
    if model_cls is None:
        raise NotFoundError("Entity model not found")

    datasource = model_cls.datasource()
    if datasource == DatasourceType.POSTGRESQL:
        return model_cls, PostgresCRUDRepository(model_cls)
    if datasource == DatasourceType.MONGODB:
        provider = mongo_collection_provider or MongoDBConnector.get_collection
        return model_cls, MongoCRUDRepository(model_cls, collection_provider=provider)
    raise ValidationError("Datasource not supported")
