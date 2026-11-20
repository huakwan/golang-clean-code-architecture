from __future__ import annotations

import logging
import math
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import fields as dataclass_fields
from dataclasses import is_dataclass
from datetime import UTC, date, datetime
from types import UnionType
from typing import Any, Union, get_args, get_origin, get_type_hints

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import DuplicateKeyError, PyMongoError

from src.domain.entities.crud import DataListResponse, DataResponse, ICRUDDataModel
from src.domain.exceptions import ConflictError, DatabaseError, NotFoundError, ValidationError
from src.domain.repositories.crud_repository import ICRUDRepository
from src.interfaces.repositories.mongodb.collection import (
    CollectionProvider,
    MongoCollectionProtocol,
    make_collection_resolver,
)
from src.shared.crud.avro_schema import generate_avro_schema
from src.shared.crud.constants import SENSITIVE_FIELD_NAMES
from src.shared.utils import format_iso_datetime

logger = logging.getLogger(__name__)

_STRING_TYPE_MAP: dict[str, Any] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "dict": dict,
    "list": list,
    "datetime": datetime,
    "date": date,
    "Any": Any,
}


def _serialize_mongo_value(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, (datetime, date)):
        return format_iso_datetime(value)
    if isinstance(value, dict):
        return {
            k: _serialize_mongo_value(v) for k, v in value.items() if k not in SENSITIVE_FIELD_NAMES
        }
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


def _validate_key_name(key: Any) -> str:
    if not isinstance(key, str) or not key or key.startswith("$") or "." in key or "\x00" in key:
        raise ValidationError(f"Invalid field name: '{key}'")
    return key


def _validate_nested_value(value: Any, *, field_name: str) -> None:
    if isinstance(value, dict):
        for nested_key, nested_val in value.items():
            _validate_key_name(nested_key)
            _validate_nested_value(nested_val, field_name=f"{field_name}.{nested_key}")
    elif isinstance(value, list):
        for item in value:
            _validate_nested_value(item, field_name=field_name)


def _resolve_string_annotation(raw: str) -> Any:
    parts = [p.strip() for p in raw.split("|")]
    if "None" in parts:
        non_none = [p for p in parts if p != "None"]
        inner = (
            _STRING_TYPE_MAP.get(non_none[0].split("[")[0].strip(), Any)
            if len(non_none) == 1
            else Any
        )
        return inner | None
    return _STRING_TYPE_MAP.get(raw.split("[")[0].strip(), Any)


def _resolve_field_types(model_cls: type[ICRUDDataModel]) -> dict[str, Any]:
    if not is_dataclass(model_cls):
        raise ValidationError("Unsupported MongoDB model schema")

    try:
        hints = get_type_hints(model_cls)
    except (NameError, TypeError, AttributeError):
        hints = {}

    field_types: dict[str, Any] = {}
    for dc_field in dataclass_fields(model_cls):
        annotation = hints.get(dc_field.name, dc_field.type)
        if isinstance(annotation, str):
            annotation = _resolve_string_annotation(annotation)
        field_types[dc_field.name] = annotation
    return field_types


def _unwrap_optional(annotation: Any) -> tuple[Any, bool]:
    origin = get_origin(annotation)
    if origin in (Union, UnionType):
        args = get_args(annotation)
        allows_none = type(None) in args
        non_none = [arg for arg in args if arg is not type(None)]
        inner = non_none[0] if len(non_none) == 1 else Any
        return inner, allows_none
    return annotation, False


def _coerce_bool(value: Any, *, field_name: str, from_query: bool) -> bool:
    if isinstance(value, bool):
        return value
    if from_query and isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "1"):
            return True
        if lowered in ("false", "0"):
            return False
    raise ValidationError(f"Field '{field_name}' must be a boolean")


def _coerce_int(value: Any, *, field_name: str, from_query: bool) -> int:
    if isinstance(value, bool):
        raise ValidationError(f"Field '{field_name}' must be an integer")
    if isinstance(value, int):
        return value
    if from_query and isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            pass
    raise ValidationError(f"Field '{field_name}' must be an integer")


def _coerce_float(value: Any, *, field_name: str, from_query: bool) -> float:
    if isinstance(value, bool):
        raise ValidationError(f"Field '{field_name}' must be a number")
    if isinstance(value, (int, float)):
        parsed = float(value)
        if math.isfinite(parsed):
            return parsed
        raise ValidationError(f"Field '{field_name}' must be a finite number")
    if from_query and isinstance(value, str):
        try:
            parsed = float(value)
        except ValueError as exc:
            raise ValidationError(f"Field '{field_name}' must be a number") from exc
        if math.isfinite(parsed):
            return parsed
        raise ValidationError(f"Field '{field_name}' must be a finite number")
    raise ValidationError(f"Field '{field_name}' must be a number")


def _coerce_datetime(value: Any, *, field_name: str) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    raise ValidationError(f"Field '{field_name}' must be an ISO-8601 datetime")


def _coerce_date(value: Any, *, field_name: str) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    raise ValidationError(f"Field '{field_name}' must be an ISO-8601 date")


def _coerce_value(value: Any, annotation: Any, *, field_name: str, from_query: bool) -> Any:
    inner, allows_none = _unwrap_optional(annotation)
    if value is None:
        if allows_none and not from_query:
            return None
        raise ValidationError(f"Field '{field_name}' cannot be null")

    if from_query and isinstance(value, (dict, list)):
        raise ValidationError(f"Invalid filter value for '{field_name}'")

    origin = get_origin(inner)
    target = origin if origin is not None else inner

    if target in (dict, list):
        if from_query:
            raise ValidationError(f"Filtering on '{field_name}' is not supported")
        if not isinstance(value, target):
            raise ValidationError(f"Field '{field_name}' must be a {target.__name__}")
        _validate_nested_value(value, field_name=field_name)
        return value

    if target is bool:
        return _coerce_bool(value, field_name=field_name, from_query=from_query)
    if target is int:
        return _coerce_int(value, field_name=field_name, from_query=from_query)
    if target is float:
        return _coerce_float(value, field_name=field_name, from_query=from_query)
    if target is str:
        if isinstance(value, str):
            return value
        raise ValidationError(f"Field '{field_name}' must be a string")
    if target is datetime:
        return _coerce_datetime(value, field_name=field_name)
    if target is date:
        return _coerce_date(value, field_name=field_name)

    _validate_nested_value(value, field_name=field_name)
    return value


@contextmanager
def _handle_mongo_errors(operation: str) -> Iterator[None]:
    try:
        yield
    except DuplicateKeyError as exc:
        raise ConflictError("Record violates a unique constraint") from exc
    except PyMongoError as exc:
        logger.warning("MongoDB %s failed", operation, exc_info=True)
        raise DatabaseError("Database operation failed") from exc


class MongoCRUDRepository(ICRUDRepository):
    """Generic PyMongo repository for any registered MongoDB dataclass document."""

    def __init__(
        self,
        model_cls: type[ICRUDDataModel],
        *,
        collection: MongoCollectionProtocol | None = None,
        collection_provider: CollectionProvider | None = None,
    ) -> None:
        self._model_cls = model_cls
        self._field_types = _resolve_field_types(model_cls)
        self._resolve_collection = make_collection_resolver(
            collection,
            collection_provider,
            model_cls.table_name(),
        )

    @property
    def collection(self) -> MongoCollectionProtocol:
        return self._resolve_collection()

    def _build_query_filters(self, filters: dict[str, Any] | None) -> dict[str, Any]:
        if not filters:
            return {}
        query: dict[str, Any] = {}
        for key, raw_value in filters.items():
            _validate_key_name(key)
            if key in SENSITIVE_FIELD_NAMES or key not in self._field_types:
                raise ValidationError(f"Invalid filter field: '{key}'")
            if key == "id":
                if not isinstance(raw_value, str):
                    raise ValidationError("Invalid filter value for 'id'")
                query["_id"] = _build_id_filter(raw_value)["_id"]
            else:
                query[key] = _coerce_value(
                    raw_value,
                    self._field_types[key],
                    field_name=key,
                    from_query=True,
                )
        return query

    def _sanitize_write_payload(
        self,
        payload: dict[str, Any],
        *,
        empty_message: str,
    ) -> dict[str, Any]:
        sanitized: dict[str, Any] = {}
        for key, raw_value in payload.items():
            if key in ("id", "_id"):
                continue
            _validate_key_name(key)
            if key in SENSITIVE_FIELD_NAMES or key not in self._field_types:
                raise ValidationError(f"Invalid field: '{key}'")
            sanitized[key] = _coerce_value(
                raw_value,
                self._field_types[key],
                field_name=key,
                from_query=False,
            )
        if not sanitized:
            raise ValidationError(empty_message)
        return sanitized

    def describe_data_source(self) -> dict[str, Any]:
        return generate_avro_schema(self._model_cls)

    def get_one_by_id(self, record_id: str) -> DataResponse:
        with _handle_mongo_errors("find_one"):
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
        query = self._build_query_filters(filters)
        with _handle_mongo_errors("list"):
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
        doc = self._sanitize_write_payload(payload, empty_message="No creatable fields provided")
        if "created_at" in self._field_types:
            doc.setdefault("created_at", datetime.now(UTC))
        with _handle_mongo_errors("create"):
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
        updates = self._sanitize_write_payload(
            payload,
            empty_message="No updatable fields provided",
        )
        id_filter = _build_id_filter(record_id)
        with _handle_mongo_errors("update"):
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
        with _handle_mongo_errors("delete"):
            result = self.collection.delete_one(_build_id_filter(record_id))
        if result.deleted_count == 0:
            raise NotFoundError(f"Record '{record_id}' not found")
