from __future__ import annotations

from threading import Lock
from typing import Any

from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from src.config.env_config import get_config


class MongoDBConnector:
    """Thread-safe lazy singleton wrapper around PyMongo's MongoClient."""

    _lock = Lock()
    _client: MongoClient[dict[str, Any]] | None = None

    @classmethod
    def get_client(cls) -> MongoClient[dict[str, Any]]:
        if cls._client is None:
            with cls._lock:
                if cls._client is None:
                    cfg = get_config()
                    cls._client = MongoClient(
                        cfg.mongodb_uri,
                        serverSelectionTimeoutMS=3000,
                        connectTimeoutMS=3000,
                    )
        return cls._client

    @classmethod
    def get_database(cls) -> Database[dict[str, Any]]:
        cfg = get_config()
        return cls.get_client()[cfg.mongodb_db_name]

    @classmethod
    def get_collection(cls, name: str) -> Collection[dict[str, Any]]:
        return cls.get_database()[name]

    @classmethod
    def reset(cls) -> None:
        with cls._lock:
            if cls._client is not None:
                cls._client.close()
                cls._client = None
