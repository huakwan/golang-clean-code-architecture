from __future__ import annotations

import pytest

from src.domain.exceptions import NotFoundError
from src.infrastructure.database.mongodb.models import ActivityLogDocument
from src.interfaces.repositories.mongodb.activity_logger import MongoActivityLogger
from src.interfaces.repositories.mongodb.crud_repository import MongoCRUDRepository
from src.tests.conftest import InMemoryMongoCollection


def test_mongo_activity_logger_and_crud_repository_roundtrip() -> None:
    collection = InMemoryMongoCollection()
    logger = MongoActivityLogger(collection=collection)
    repo = MongoCRUDRepository(ActivityLogDocument, collection=collection)

    logger.record(
        user_id=1,
        action="USER_LOGIN",
        resource="users",
        status="success",
        ip_address="127.0.0.1",
        metadata={"email": "jane@example.com"},
    )
    logger.record(
        user_id=1,
        action="USER_LOGOUT",
        resource="users",
        status="success",
    )

    page1 = repo.get_list(page=1, page_size=1)
    assert page1.total_data == 2
    assert page1.total_page == 2
    assert len(page1.data) == 1
    assert page1.data_schema is not None
    assert page1.data_schema["name"] == "activity-logs"

    record_id = page1.data[0]["id"]
    single = repo.get_one_by_id(record_id)
    assert single.data["id"] == record_id

    repo.delete(record_id)
    assert repo.get_list(page=1, page_size=10).total_data == 1

    with pytest.raises(NotFoundError):
        repo.get_one_by_id(record_id)


def test_mongo_activity_logger_swallows_pymongo_errors_fail_safely() -> None:
    from unittest.mock import MagicMock

    from pymongo.errors import PyMongoError

    broken_collection = MagicMock()
    broken_collection.insert_one.side_effect = PyMongoError("connection refused")
    logger = MongoActivityLogger(collection=broken_collection)

    logger.record(
        user_id=1,
        action="USER_LOGIN",
        resource="users",
        status="success",
    )
    broken_collection.insert_one.assert_called_once()


def test_mongo_crud_empty_update_raises_validation_error() -> None:
    from src.domain.exceptions import ValidationError

    collection = InMemoryMongoCollection()
    repo = MongoCRUDRepository(ActivityLogDocument, collection=collection)
    with pytest.raises(ValidationError, match="No updatable fields provided"):
        repo.update("abc", {})
