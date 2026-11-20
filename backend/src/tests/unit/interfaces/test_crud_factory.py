from __future__ import annotations

import pytest

from src.config.crud_models import get_crud_model_registry
from src.domain.exceptions import NotFoundError, ValidationError
from src.infrastructure.database.mongodb.models import ActivityLogDocument
from src.infrastructure.database.postgres.models import UserModel, UserTokenModel
from src.interfaces.repositories.crud.factory import build_crud_repository
from src.interfaces.repositories.mongodb.crud_repository import MongoCRUDRepository
from src.interfaces.repositories.postgres.crud_repository import PostgresCRUDRepository
from src.tests.conftest import InMemoryMongoCollection


def test_crud_factory_routes_postgres_slugs() -> None:
    registry = get_crud_model_registry()
    model_cls, repo = build_crud_repository("users", registry=registry)
    assert model_cls is UserModel
    assert isinstance(repo, PostgresCRUDRepository)

    token_cls, token_repo = build_crud_repository("user-tokens", registry=registry)
    assert token_cls is UserTokenModel
    assert isinstance(token_repo, PostgresCRUDRepository)


def test_crud_factory_routes_mongodb_slugs_and_requires_provider() -> None:
    registry = get_crud_model_registry()
    with pytest.raises(ValidationError, match="MongoDB collection provider is required"):
        build_crud_repository("activity-logs", registry=registry)

    model_cls, repo = build_crud_repository(
        "activity-logs",
        registry=registry,
        mongo_collection_provider=lambda _name: InMemoryMongoCollection(),
    )
    assert model_cls is ActivityLogDocument
    assert isinstance(repo, MongoCRUDRepository)


def test_crud_factory_unknown_slug_raises_not_found() -> None:
    registry = get_crud_model_registry()
    with pytest.raises(NotFoundError, match="Entity model not found"):
        build_crud_repository("does-not-exist", registry=registry)
