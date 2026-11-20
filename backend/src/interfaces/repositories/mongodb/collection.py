from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class MongoCollectionProtocol(Protocol):
    """Minimal PyMongo collection contract needed by activity logger and CRUD repository."""

    def insert_one(self, document: dict[str, Any], /) -> Any: ...
    def find_one(self, filter_query: dict[str, Any], /) -> dict[str, Any] | None: ...
    def find(self, filter_query: dict[str, Any], /) -> Any: ...
    def count_documents(self, filter_query: dict[str, Any], /) -> int: ...
    def update_one(self, filter_query: dict[str, Any], update: dict[str, Any], /) -> Any: ...
    def delete_one(self, filter_query: dict[str, Any], /) -> Any: ...


CollectionProvider = Callable[[str], MongoCollectionProtocol]


def make_collection_resolver(
    collection: MongoCollectionProtocol | None,
    collection_provider: CollectionProvider | None,
    collection_name: str,
) -> Callable[[], MongoCollectionProtocol]:
    if collection is not None:
        return lambda: collection
    if collection_provider is not None:
        return lambda: collection_provider(collection_name)
    raise ValueError("Provide either 'collection' or 'collection_provider'")
