from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, models, transaction

from src.domain.entities.crud import DataListResponse, DataResponse
from src.domain.exceptions import ConflictError, NotFoundError, ValidationError
from src.domain.repositories.crud_repository import ICRUDRepository
from src.shared.authentication.password import hash_password
from src.shared.crud.avro_schema import generate_avro_schema
from src.shared.crud.constants import SENSITIVE_FIELD_NAMES
from src.shared.utils import format_iso_datetime


def _serialize_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return format_iso_datetime(value)
    return value


def _is_readonly_field(field: models.Field[Any, Any]) -> bool:
    return bool(
        field.primary_key
        or getattr(field, "auto_now", False)
        or getattr(field, "auto_now_add", False)
    )


def _apply_filters(
    queryset: models.QuerySet[Any],
    model_cls: type[models.Model],
    filters: dict[str, Any] | None,
) -> models.QuerySet[Any]:
    if not filters:
        return queryset
    concrete = model_cls._meta.concrete_fields
    valid_field_names = {f.name for f in concrete} | {f.attname for f in concrete}
    safe_filters = {
        key: value
        for key, value in filters.items()
        if key in valid_field_names and key not in SENSITIVE_FIELD_NAMES
    }
    return queryset.filter(**safe_filters) if safe_filters else queryset


def _serialize_instance(instance: models.Model) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field in instance._meta.concrete_fields:
        if field.name in SENSITIVE_FIELD_NAMES:
            continue
        if field.is_relation:
            result[field.attname] = getattr(instance, field.attname)
        else:
            result[field.name] = _serialize_value(getattr(instance, field.name))
    return result


class PostgresCRUDRepository(ICRUDRepository):
    """Generic Django ORM repository for any registered PostgreSQL model."""

    def __init__(self, model_cls: type[models.Model]) -> None:
        self._model_cls = model_cls

    def _parse_pk(self, record_id: str) -> int:
        try:
            return int(record_id)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"Invalid record id: '{record_id}'") from exc

    def _extract_writable_fields(
        self,
        payload: dict[str, Any],
        *,
        is_create: bool,
    ) -> dict[str, Any]:
        writable: dict[str, Any] = {}
        for field in self._model_cls._meta.concrete_fields:
            if _is_readonly_field(field):
                continue

            if field.is_relation:
                if field.attname in payload:
                    writable[field.attname] = payload[field.attname]
                elif field.name in payload:
                    writable[field.attname] = payload[field.name]
            elif field.name in payload:
                val = payload[field.name]
                if field.name == "password":
                    if not isinstance(val, str) or not val.strip():
                        if is_create:
                            raise ValidationError("password is required")
                        continue
                    val = hash_password(val)
                writable[field.name] = val
        return writable

    def describe_data_source(self) -> dict[str, Any]:
        return generate_avro_schema(self._model_cls)

    def get_one_by_id(self, record_id: str) -> DataResponse:
        pk = self._parse_pk(record_id)
        instance = self._model_cls.objects.filter(pk=pk).first()
        if instance is None:
            raise NotFoundError(f"Record '{record_id}' not found")
        return DataResponse(
            code=0,
            data=_serialize_instance(instance),
            message="",
            data_schema=self.describe_data_source(),
        )

    def get_list(
        self,
        page: int = 1,
        page_size: int = 10,
        filters: dict[str, Any] | None = None,
    ) -> DataListResponse:
        try:
            queryset = _apply_filters(self._model_cls.objects.all(), self._model_cls, filters)
            total_data = queryset.count()
            total_page = math.ceil(total_data / page_size) if total_data > 0 else 0
            offset = (page - 1) * page_size
            items = [_serialize_instance(obj) for obj in queryset[offset : offset + page_size]]
        except (ValueError, DjangoValidationError) as exc:
            raise ValidationError("Invalid filter parameter") from exc

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
        data = self._extract_writable_fields(payload, is_create=True)
        try:
            with transaction.atomic():
                instance = self._model_cls.objects.create(**data)
        except IntegrityError as exc:
            raise ConflictError("Record violates a unique or relational constraint") from exc
        except (TypeError, ValueError, DjangoValidationError) as exc:
            raise ValidationError("Invalid field value") from exc

        return DataResponse(
            code=0,
            data=_serialize_instance(instance),
            message="created",
            data_schema=self.describe_data_source(),
        )

    def update(self, record_id: str, payload: dict[str, Any]) -> DataResponse:
        pk = self._parse_pk(record_id)
        instance = self._model_cls.objects.filter(pk=pk).first()
        if instance is None:
            raise NotFoundError(f"Record '{record_id}' not found")

        data = self._extract_writable_fields(payload, is_create=False)
        for key, value in data.items():
            setattr(instance, key, value)

        try:
            with transaction.atomic():
                instance.save()
        except IntegrityError as exc:
            raise ConflictError("Record violates a unique or relational constraint") from exc
        except (TypeError, ValueError, DjangoValidationError) as exc:
            raise ValidationError("Invalid field value") from exc

        return DataResponse(
            code=0,
            data=_serialize_instance(instance),
            message="updated",
            data_schema=self.describe_data_source(),
        )

    def delete(self, record_id: str) -> None:
        pk = self._parse_pk(record_id)
        deleted_count, _ = self._model_cls.objects.filter(pk=pk).delete()
        if deleted_count == 0:
            raise NotFoundError(f"Record '{record_id}' not found")
