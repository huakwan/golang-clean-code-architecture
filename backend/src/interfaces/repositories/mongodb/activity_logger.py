from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from pymongo.errors import PyMongoError

from src.domain.repositories.activity_logger import IActivityLogger
from src.interfaces.repositories.mongodb.collection import (
    CollectionProvider,
    MongoCollectionProtocol,
    make_collection_resolver,
)

logger = logging.getLogger(__name__)


class MongoActivityLogger(IActivityLogger):
    """Fail-safe audit trail logger writing to the MongoDB 'activity_logs' collection."""

    def __init__(
        self,
        *,
        collection: MongoCollectionProtocol | None = None,
        collection_provider: CollectionProvider | None = None,
    ) -> None:
        self._resolve_collection = make_collection_resolver(
            collection,
            collection_provider,
            "activity_logs",
        )

    @property
    def collection(self) -> MongoCollectionProtocol:
        return self._resolve_collection()

    def record(
        self,
        *,
        user_id: int | None,
        action: str,
        resource: str,
        status: str,
        ip_address: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        try:
            self.collection.insert_one(
                {
                    "user_id": user_id,
                    "action": action,
                    "resource": resource,
                    "status": status,
                    "ip_address": ip_address,
                    "metadata": metadata or {},
                    "created_at": datetime.now(UTC),
                }
            )
        except (PyMongoError, OSError):
            logger.warning(
                "MongoDB activity log write failed for action=%s",
                action,
                exc_info=True,
            )
