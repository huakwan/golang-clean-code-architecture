from __future__ import annotations

import pytest

from src.domain.exceptions import NotFoundError
from src.infrastructure.database.mongodb.models import ActivityLogDocument
from src.infrastructure.database.postgres.models import UserModel, UserTokenModel
from src.interfaces.repositories.crud.factory import get_crud_repository
from src.interfaces.repositories.mongodb.crud_repository import MongoCRUDRepository
from src.interfaces.repositories.postgres.crud_repository import PostgresCRUDRepository


def test_crud_factory_routes_postgres_slugs() -> None:
    model_cls, repo = get_crud_repository("users")
    assert model_cls is UserModel
    assert isinstance(repo, PostgresCRUDRepository)

    token_cls, token_repo = get_crud_repository("user-tokens")
    assert token_cls is UserTokenModel
    assert isinstance(token_repo, PostgresCRUDRepository)


def test_crud_factory_routes_mongodb_slugs() -> None:
    model_cls, repo = get_crud_repository("activity-logs")
    assert model_cls is ActivityLogDocument
    assert isinstance(repo, MongoCRUDRepository)


def test_crud_factory_unknown_slug_raises_not_found() -> None:
    with pytest.raises(NotFoundError, match="Entity model not found"):
        get_crud_repository("does-not-exist")
