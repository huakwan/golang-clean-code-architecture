from __future__ import annotations

from collections.abc import Callable
from typing import Any

CollectionProvider = Callable[[str], Any]


def make_collection_resolver(
    collection: Any | None,
    collection_provider: CollectionProvider | None,
    collection_name: str,
) -> Callable[[], Any]:
    if collection is not None:
        return lambda: collection
    if collection_provider is not None:
        return lambda: collection_provider(collection_name)
    raise ValueError("Provide either 'collection' or 'collection_provider'")
