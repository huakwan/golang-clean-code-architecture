from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import pytest
from bson import ObjectId

os.environ.setdefault("DJANGO_USE_SQLITE", "1")


@dataclass
class _InsertOneResult:
    inserted_id: ObjectId


@dataclass
class _UpdateResult:
    matched_count: int


@dataclass
class _DeleteResult:
    deleted_count: int


class _InMemoryCursor:
    def __init__(self, docs: list[dict[str, Any]]) -> None:
        self._docs = list(docs)

    def sort(self, key: str, direction: int) -> _InMemoryCursor:
        reverse = direction < 0
        self._docs.sort(key=lambda d: str(d.get(key, "")), reverse=reverse)
        return self

    def skip(self, count: int) -> _InMemoryCursor:
        self._docs = self._docs[count:]
        return self

    def limit(self, count: int) -> _InMemoryCursor:
        self._docs = self._docs[:count]
        return self

    def __iter__(self):
        return iter(self._docs)


class InMemoryMongoCollection:
    """Minimal in-memory PyMongo collection double for deterministic tests."""

    def __init__(self) -> None:
        self.docs: list[dict[str, Any]] = []

    def _matches(self, doc: dict[str, Any], query: dict[str, Any]) -> bool:
        for key, value in query.items():
            if doc.get(key) != value:
                return False
        return True

    def insert_one(self, document: dict[str, Any]) -> _InsertOneResult:
        stored = dict(document)
        stored.setdefault("_id", ObjectId())
        self.docs.append(stored)
        return _InsertOneResult(inserted_id=stored["_id"])

    def find_one(self, query: dict[str, Any]) -> dict[str, Any] | None:
        for doc in self.docs:
            if self._matches(doc, query):
                return dict(doc)
        return None

    def find(self, query: dict[str, Any]) -> _InMemoryCursor:
        matched = [dict(doc) for doc in self.docs if self._matches(doc, query)]
        return _InMemoryCursor(matched)

    def count_documents(self, query: dict[str, Any]) -> int:
        return sum(1 for doc in self.docs if self._matches(doc, query))

    def update_one(self, query: dict[str, Any], update: dict[str, Any]) -> _UpdateResult:
        for doc in self.docs:
            if self._matches(doc, query):
                doc.update(update.get("$set", {}))
                return _UpdateResult(matched_count=1)
        return _UpdateResult(matched_count=0)

    def delete_one(self, query: dict[str, Any]) -> _DeleteResult:
        for idx, doc in enumerate(self.docs):
            if self._matches(doc, query):
                del self.docs[idx]
                return _DeleteResult(deleted_count=1)
        return _DeleteResult(deleted_count=0)


@pytest.fixture
def in_memory_mongo_collection(monkeypatch: pytest.MonkeyPatch) -> InMemoryMongoCollection:
    from src.infrastructure.container import reset_container
    from src.infrastructure.database.mongodb.connector import MongoDBConnector

    collection = InMemoryMongoCollection()
    monkeypatch.setattr(
        MongoDBConnector,
        "get_collection",
        classmethod(lambda cls, name: collection),
    )
    reset_container()
    yield collection
    reset_container()
