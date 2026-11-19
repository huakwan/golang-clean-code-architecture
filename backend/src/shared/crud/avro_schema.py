from __future__ import annotations

from dataclasses import fields as dataclass_fields
from dataclasses import is_dataclass
from datetime import date, datetime
from typing import Any, get_args, get_origin, get_type_hints

from src.shared.crud.constants import SENSITIVE_FIELD_NAMES
from src.shared.crud.converter import convert_name_to_crud_slug

_DJANGO_FIELD_TYPE_MAP: dict[str, str] = {
    "AutoField": "int",
    "BigAutoField": "long",
    "SmallAutoField": "int",
    "IntegerField": "int",
    "SmallIntegerField": "int",
    "PositiveIntegerField": "int",
    "PositiveSmallIntegerField": "int",
    "BigIntegerField": "long",
    "PositiveBigIntegerField": "long",
    "FloatField": "float",
    "DecimalField": "float",
    "BooleanField": "boolean",
    "CharField": "string",
    "TextField": "string",
    "EmailField": "string",
    "SlugField": "string",
    "URLField": "string",
    "UUIDField": "string",
    "DateTimeField": "datetime",
    "DateField": "datetime",
    "JSONField": "map",
}


def _model_slug(model_cls: type[Any]) -> str:
    if hasattr(model_cls, "table_name") and callable(model_cls.table_name):
        return convert_name_to_crud_slug(model_cls.table_name())
    return convert_name_to_crud_slug(model_cls.__name__)


def _python_type_to_avro(annotation: Any) -> str:
    origin = get_origin(annotation)
    if origin is not None:
        args = [arg for arg in get_args(annotation) if arg is not type(None)]
        if origin is dict:
            return "map"
        if origin is list:
            return "array"
        if len(args) == 1:
            return _python_type_to_avro(args[0])
        return "unknown"

    if annotation is bool:
        return "boolean"
    if annotation is int:
        return "int"
    if annotation is float:
        return "float"
    if annotation is str:
        return "string"
    if annotation in (datetime, date):
        return "datetime"
    if annotation is dict:
        return "map"
    return "unknown"


def _django_model_fields(
    model_cls: type[Any],
    visited: frozenset[type[Any]],
) -> list[dict[str, Any]]:
    avro_fields: list[dict[str, Any]] = []
    for field in model_cls._meta.concrete_fields:
        if field.name in SENSITIVE_FIELD_NAMES:
            continue

        internal_type = field.get_internal_type()
        if internal_type in ("ForeignKey", "OneToOneField") and field.related_model is not None:
            related = field.related_model
            entry: dict[str, Any] = {
                "name": field.attname,
                "type": "int",
            }
            avro_fields.append(entry)
            if related not in visited:
                avro_fields.append(
                    {
                        "name": field.name,
                        "type": _model_slug(related),
                        "fields": _build_schema(related, visited | {related}),
                    }
                )
            continue

        avro_fields.append(
            {
                "name": field.name,
                "type": _DJANGO_FIELD_TYPE_MAP.get(internal_type, "unknown"),
            }
        )
    return avro_fields


def _dataclass_model_fields(model_cls: type[Any]) -> list[dict[str, Any]]:
    try:
        hints = get_type_hints(model_cls)
    except (NameError, TypeError, AttributeError):
        hints = {}

    avro_fields: list[dict[str, Any]] = []
    for dc_field in dataclass_fields(model_cls):
        if dc_field.name in SENSITIVE_FIELD_NAMES:
            continue
        annotation = hints.get(dc_field.name, dc_field.type)
        avro_fields.append(
            {
                "name": dc_field.name,
                "type": _python_type_to_avro(annotation),
            }
        )
    return avro_fields


def _build_schema(model_cls: type[Any], visited: frozenset[type[Any]]) -> dict[str, Any]:
    if hasattr(model_cls, "_meta") and hasattr(model_cls._meta, "concrete_fields"):
        schema_fields = _django_model_fields(model_cls, visited)
    elif is_dataclass(model_cls):
        schema_fields = _dataclass_model_fields(model_cls)
    else:
        schema_fields = []

    return {
        "type": "record",
        "name": _model_slug(model_cls),
        "fields": schema_fields,
    }


def generate_avro_schema(model_cls: type[Any]) -> dict[str, Any]:
    """Generate an Avro-style record schema dictionary for a Django Model or dataclass."""
    return _build_schema(model_cls, frozenset({model_cls}))
