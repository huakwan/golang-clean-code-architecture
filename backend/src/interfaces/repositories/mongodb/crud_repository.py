from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from bson.errors import InvalidId

from src.domain.entities.crud import DataListResponse, DataResponse, ICRUDDataModel
from src.domain.exceptions import NotFoundError, ValidationError
from src.domain.repositories.crud_repository import ICRUDRepository
from src.interfaces.repositories.mongodb.collection import (
    CollectionProvider,
    make_collection_resolver,
)
from src.shared.crud.avro_schema import generate_avro_schema
from src.shared.crud.constants import SENSITIVE_FIELD_NAMES
from src.shared.utils import format_iso_datetime


def _serialize_mongo_value(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return format_iso_datetime(value)
    if isinstance(value, dict):
        return {k: _serialize_mongo_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serialize_mongo_value(v) for v in value]
    return value


def _serialize_document(doc: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in doc.items():
        if key in SENSITIVE_FIELD_NAMES:
            continue
        if key == "_id":
            result["id"] = str(value)
        else:
            result[key] = _serialize_mongo_value(value)
    return result


def _build_id_filter(record_id: str) -> dict[str, Any]:
    try:
        return {"_id": ObjectId(record_id)}
    except (InvalidId, TypeError):
        return {"_id": record_id}


class MongoCRUDRepository(ICRUDRepository):
    """Generic PyMongo repository for any registered MongoDB dataclass document."""

    def __init__(
        self,
        model_cls: type[ICRUDDataModel],
        *,
        collection: Any | None = None,
        collection_provider: CollectionProvider | None = None,
    ) -> None:
        self._model_cls = model_cls
        self._resolve_collection = make_collection_resolver(
            collection,
            collection_provider,
            model_cls.table_name(),
        )

    @property
    def collection(self) -> Any:
        return self._resolve_collection()

    def describe_data_source(self) -> dict[str, Any]:
        return generate_avro_schema(self._model_cls)

    def get_one_by_id(self, record_id: str) -> DataResponse:
        doc = self.collection.find_one(_build_id_filter(record_id))
        if doc is None:
            raise NotFoundError(f"Record '{record_id}' not found")
        return DataResponse(
            code=0,
            data=_serialize_document(doc),
            message="",
            data_schema=self.describe_data_source(),
        )

    def get_list(
        self,
        page: int = 1,
        page_size: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> DataListResponse:
        query = {
            k: v
            for k, v in (filters or {}).items()
            if k not in SENSITIVE_FIELD_NAMES
        }
        total_data = int(self.collection.count_documents(query))
        total_page = math.ceil(total_data / page_size) if total_data > 0 else 0
        skip = (page - 1) * page_size

        cursor = self.collection.find(query).sort("_id", -1).skip(skip).limit(page_size)
        items = [_serialize_document(doc) for doc in cursor]

        return DataListResponse(
            code=0,
            data=items,
            page=page,
            page_size=page_size,
            total_page=total_page,
            total_data=total_data,
            message="",
            data_schema=self.describe_data_source(),
        )

    def create(self, payload: dict[str, Any]) -> DataResponse:
        doc = {k: v for k, v in payload.items() if k not in ("id", "_id")}
        doc.setdefault("created_at", datetime.now(UTC))
        inserted = self.collection.insert_one(doc)
        created = self.collection.find_one({"_id": inserted.inserted_id}) or {
            **doc,
            "_id": inserted.inserted_id,
        }
        return DataResponse(
            code=0,
            data=_serialize_document(created),
            message="created",
            data_schema=self.describe_data_source(),
        )

    def update(self, record_id: str, payload: dict[str, Any]) -> DataResponse:
        updates = {k: v for k, v in payload.items() if k not in ("id", "_id")}
        if not updates:
            raise ValidationError("No updatable fields provided")
        id_filter = _build_id_filter(record_id)
        result = self.collection.update_one(id_filter, {"$set": updates})
        if result.matched_count == 0:
            raise NotFoundError(f"Record '{record_id}' not found")
        updated = self.collection.find_one(id_filter)
        return DataResponse(
            code=0,
            data=_serialize_document(updated) if updated else {"id": record_id, **updates},
            message="updated",
            data_schema=self.describe_data_source(),
        )

    def delete(self, record_id: str) -> None:
        result = self.collection.delete_one(_build_id_filter(record_id))
        if result.deleted_count == 0:
            raise NotFoundError(f"Record '{record_id}' not found")
