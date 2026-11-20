from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock

import pytest
from bson import ObjectId
from pymongo.errors import DuplicateKeyError, PyMongoError

from src.domain.entities.crud import DatasourceType, ICRUDDataModel
from src.domain.exceptions import ConflictError, DatabaseError, NotFoundError, ValidationError
from src.infrastructure.database.mongodb.models import ActivityLogDocument
from src.interfaces.repositories.mongodb.activity_logger import MongoActivityLogger
from src.interfaces.repositories.mongodb.crud_repository import MongoCRUDRepository
from src.tests.conftest import InMemoryMongoCollection


@dataclass(frozen=True)
class SampleMongoItem(ICRUDDataModel):
    id: str = ""
    user_id: int | None = None
    title: str = ""
    active: bool = True
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    password: str = ""

    @classmethod
    def table_name(cls) -> str:
        return "sample_items"

    @classmethod
    def datasource(cls) -> DatasourceType:
        return DatasourceType.MONGODB


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
    collection = InMemoryMongoCollection()
    repo = MongoCRUDRepository(SampleMongoItem, collection=collection)
    with pytest.raises(ValidationError, match="No updatable fields provided"):
        repo.update("abc", {})
    with pytest.raises(ValidationError, match="No updatable fields provided"):
        repo.update("abc", {"id": "ignored", "_id": "ignored"})


@pytest.mark.parametrize(
    "bad_filter",
    [
        {"$where": "1"},
        {"$ne": "x"},
        {"metadata.email": "a@b.com"},
        {"nonexistent": "x"},
        {"password": "x"},
        {"access": "x"},
        {"refresh": "x"},
        {"action": {"$ne": ""}},
        {"action": ["USER_LOGIN"]},
        {"metadata": "anything"},
        {"user_id": "not-an-int"},
    ],
)
def test_mongo_crud_get_list_rejects_invalid_and_injection_filters(
    bad_filter: dict[str, Any],
) -> None:
    collection = InMemoryMongoCollection()
    repo = MongoCRUDRepository(ActivityLogDocument, collection=collection)
    with pytest.raises(ValidationError):
        repo.get_list(page=1, page_size=10, filters=bad_filter)


def test_mongo_crud_get_list_allows_valid_filters_and_coerces_types() -> None:
    collection = InMemoryMongoCollection()
    logger = MongoActivityLogger(collection=collection)
    repo = MongoCRUDRepository(ActivityLogDocument, collection=collection)

    logger.record(user_id=1, action="USER_LOGIN", resource="users", status="success")
    logger.record(user_id=2, action="USER_REGISTER", resource="users", status="success")

    res = repo.get_list(page=1, page_size=10, filters={"user_id": "1", "action": "USER_LOGIN"})
    assert res.total_data == 1
    assert res.data[0]["user_id"] == 1
    assert res.data[0]["action"] == "USER_LOGIN"


@pytest.mark.parametrize(
    "bad_payload",
    [
        {},
        {"id": "123", "_id": "123"},
        {"unknown_field": "x"},
        {"$set": {"title": "hacked"}},
        {"metadata.nested": "x"},
        {"password": "secret"},
        {"access": "token"},
        {"refresh": "token"},
        {"metadata": {"$set": "bad"}},
        {"metadata": {"a.b": 1}},
        {"metadata": {"items": [{"$ne": 1}]}},
        {"user_id": "not-int"},
        {"user_id": True},
        {"score": True},
        {"title": 123},
        {"metadata": "not-dict"},
        {"tags": "not-list"},
        {"active": "yes"},
        {"created_at": "bad-date"},
    ],
)
def test_mongo_crud_create_and_update_reject_invalid_payloads(
    bad_payload: dict[str, Any],
) -> None:
    collection = InMemoryMongoCollection()
    repo = MongoCRUDRepository(SampleMongoItem, collection=collection)
    inserted = collection.insert_one(
        {
            "user_id": 1,
            "title": "Existing",
            "active": True,
            "score": 1.0,
            "metadata": {},
            "tags": [],
            "created_at": datetime.now(UTC),
        }
    )
    record_id = str(inserted.inserted_id)

    with pytest.raises(ValidationError):
        repo.create(bad_payload)

    with pytest.raises(ValidationError):
        repo.update(record_id, bad_payload)


def test_mongo_crud_create_and_update_valid_payloads_and_coerces_datetime() -> None:
    collection = InMemoryMongoCollection()
    repo = MongoCRUDRepository(SampleMongoItem, collection=collection)

    created = repo.create(
        {
            "id": "client-supplied-id",
            "_id": "client-supplied-oid",
            "user_id": None,
            "title": "Valid Item",
            "active": False,
            "score": 4.5,
            "metadata": {"source": "api", "nested": {"ok": True}},
            "tags": ["a", "b"],
            "created_at": "2026-11-20T08:00:00Z",
        }
    )
    record_id = created.data["id"]
    assert record_id != "client-supplied-id"
    assert created.data["title"] == "Valid Item"
    assert created.data["active"] is False
    assert created.data["score"] == 4.5
    assert created.data["user_id"] is None

    updated = repo.update(
        record_id,
        {
            "id": "ignored",
            "user_id": 42,
            "title": "Updated Item",
        },
    )
    assert updated.data["user_id"] == 42
    assert updated.data["title"] == "Updated Item"


def test_mongo_crud_redacts_sensitive_fields_recursively_on_read() -> None:
    collection = InMemoryMongoCollection()
    repo = MongoCRUDRepository(SampleMongoItem, collection=collection)

    oid = ObjectId()
    collection.docs.append(
        {
            "_id": oid,
            "user_id": 7,
            "title": "SecretDoc",
            "password": "hashed-pw",
            "access": "top-access",
            "refresh": "top-refresh",
            "metadata": {
                "email": "a@b.com",
                "password": "nested-pw",
                "access": "nested-access",
                "refresh": "nested-refresh",
                "history": [
                    {"ok": 1, "access": "list-access", "refresh": "list-refresh"},
                    {"password": "list-pw", "note": "keep"},
                ],
            },
        }
    )

    single = repo.get_one_by_id(str(oid)).data
    listing = repo.get_list(page=1, page_size=10).data[0]

    for data in (single, listing):
        assert "password" not in data
        assert "access" not in data
        assert "refresh" not in data
        assert data["metadata"]["email"] == "a@b.com"
        assert "password" not in data["metadata"]
        assert "access" not in data["metadata"]
        assert "refresh" not in data["metadata"]
        assert data["metadata"]["history"] == [{"ok": 1}, {"note": "keep"}]


def test_mongo_crud_translates_pymongo_errors_to_database_and_conflict_errors() -> None:
    broken = MagicMock()
    broken.find_one.side_effect = PyMongoError("connection lost")
    broken.count_documents.side_effect = PyMongoError("connection lost")
    broken.find.side_effect = PyMongoError("connection lost")
    broken.insert_one.side_effect = PyMongoError("write failed")
    broken.update_one.side_effect = PyMongoError("update failed")
    broken.delete_one.side_effect = PyMongoError("delete failed")

    repo = MongoCRUDRepository(SampleMongoItem, collection=broken)

    with pytest.raises(DatabaseError):
        repo.get_one_by_id(str(ObjectId()))
    with pytest.raises(DatabaseError):
        repo.get_list()
    with pytest.raises(DatabaseError):
        repo.create({"title": "test"})
    with pytest.raises(DatabaseError):
        repo.update(str(ObjectId()), {"title": "test"})
    with pytest.raises(DatabaseError):
        repo.delete(str(ObjectId()))

    dup = MagicMock()
    dup.insert_one.side_effect = DuplicateKeyError("E11000 duplicate key")
    dup.update_one.side_effect = DuplicateKeyError("E11000 duplicate key")
    dup_repo = MongoCRUDRepository(SampleMongoItem, collection=dup)

    with pytest.raises(ConflictError):
        dup_repo.create({"title": "dup"})
    with pytest.raises(ConflictError):
        dup_repo.update(str(ObjectId()), {"title": "dup"})
