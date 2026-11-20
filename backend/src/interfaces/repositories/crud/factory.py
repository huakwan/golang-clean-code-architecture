from __future__ import annotations

from collections.abc import Mapping

from src.domain.entities.crud import DatasourceType, ICRUDDataModel
from src.domain.exceptions import NotFoundError, ValidationError
from src.domain.repositories.crud_repository import ICRUDRepository
from src.interfaces.repositories.mongodb.collection import CollectionProvider
from src.interfaces.repositories.mongodb.crud_repository import MongoCRUDRepository
from src.interfaces.repositories.postgres.crud_repository import PostgresCRUDRepository


def build_crud_repository(
    slug: str,
    *,
    registry: Mapping[str, type[ICRUDDataModel]],
    mongo_collection_provider: CollectionProvider | None = None,
) -> tuple[type[ICRUDDataModel], ICRUDRepository]:
    """Resolve an entity slug to its registered model class and datasource repository."""
    model_cls = registry.get(slug)
    if model_cls is None:
        raise NotFoundError("Entity model not found")

    datasource = model_cls.datasource()
    if datasource == DatasourceType.POSTGRESQL:
        return model_cls, PostgresCRUDRepository(model_cls)
    if datasource == DatasourceType.MONGODB:
        if mongo_collection_provider is None:
            raise ValidationError("MongoDB collection provider is required")
        return model_cls, MongoCRUDRepository(
            model_cls,
            collection_provider=mongo_collection_provider,
        )
    raise ValidationError("Datasource not supported")
