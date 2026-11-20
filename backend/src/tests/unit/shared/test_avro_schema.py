from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.domain.entities.crud import DatasourceType, ICRUDDataModel
from src.shared.crud.avro_schema import generate_avro_schema


@dataclass
class SampleMongoDoc(ICRUDDataModel):
    id: str = ""
    user_id: int = 0
    action: str = ""
    is_active: bool = True
    score: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime | None = None
    password: str = ""

    @classmethod
    def table_name(cls) -> str:
        return "sample_docs"

    @classmethod
    def datasource(cls) -> DatasourceType:
        return DatasourceType.MONGODB


def test_generate_avro_schema_for_dataclass_document() -> None:
    schema = generate_avro_schema(SampleMongoDoc)

    assert schema["type"] == "record"
    assert schema["name"] == "sample-docs"

    fields_by_name = {f["name"]: f for f in schema["fields"]}
    assert "password" not in fields_by_name
    assert fields_by_name["id"]["type"] == "string"
    assert fields_by_name["user_id"]["type"] == "int"
    assert fields_by_name["action"]["type"] == "string"
    assert fields_by_name["is_active"]["type"] == "boolean"
    assert fields_by_name["score"]["type"] == "float"
    assert fields_by_name["metadata"]["type"] == "map"
    assert fields_by_name["created_at"]["type"] == "datetime"


def test_generate_avro_schema_for_django_models_hides_password_and_nests_fk() -> None:
    from src.infrastructure.database.postgres.models import UserModel, UserTokenModel

    user_schema = generate_avro_schema(UserModel)
    assert user_schema["type"] == "record"
    assert user_schema["name"] == "users"
    user_field_names = {f["name"] for f in user_schema["fields"]}
    assert "password" not in user_field_names
    expected_fields = {"id", "email", "first_name", "last_name", "created_at", "updated_at"}
    assert expected_fields <= user_field_names

    token_schema = generate_avro_schema(UserTokenModel)
    assert token_schema["name"] == "user-tokens"
    token_fields = {f["name"]: f for f in token_schema["fields"]}
    assert "access" not in token_fields
    assert "refresh" not in token_fields
    assert token_fields["user"]["type"] == "users"
    assert token_fields["user"]["fields"]["name"] == "users"


def test_generate_avro_schema_uses_cache_returns_defensive_copy_and_resolves_fk_target() -> None:
    from types import SimpleNamespace

    from src.infrastructure.database.postgres.models import UserModel
    from src.shared.crud import avro_schema

    avro_schema._generate_avro_schema_cached.cache_clear()
    first = generate_avro_schema(UserModel)
    first["fields"].append({"name": "mutated", "type": "string"})
    second = generate_avro_schema(UserModel)

    assert all(f["name"] != "mutated" for f in second["fields"])
    assert avro_schema._generate_avro_schema_cached.cache_info().hits >= 1

    target_pk = SimpleNamespace(
        name="id",
        attname="id",
        get_internal_type=lambda: "BigAutoField",
        related_model=None,
    )

    class _FakeTargetModel:
        _meta = SimpleNamespace(concrete_fields=[target_pk])

        @classmethod
        def table_name(cls) -> str:
            return "big_targets"

    fk_field = SimpleNamespace(
        name="target",
        attname="target_id",
        get_internal_type=lambda: "ForeignKey",
        related_model=_FakeTargetModel,
        target_field=target_pk,
    )

    class _FakeSourceModel:
        _meta = SimpleNamespace(concrete_fields=[fk_field])

        @classmethod
        def table_name(cls) -> str:
            return "child_models"

    fk_schema = generate_avro_schema(_FakeSourceModel)
    fields_by_name = {f["name"]: f for f in fk_schema["fields"]}
    assert fields_by_name["target_id"]["type"] == "long"
