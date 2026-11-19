from __future__ import annotations

from django.db import models

from src.domain.entities.crud import ALL_CRUD_OPERATIONS, DatasourceType, ICRUDDataModel


class _PostgresCRUDMixin:
    @classmethod
    def datasource(cls) -> DatasourceType:
        return DatasourceType.POSTGRESQL

    @classmethod
    def allowed_operations(cls) -> frozenset[str]:
        return ALL_CRUD_OPERATIONS


class UserModel(_PostgresCRUDMixin, models.Model):
    id = models.AutoField(primary_key=True)
    email = models.EmailField(max_length=255, unique=True, db_index=True)
    password = models.CharField(max_length=255)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "users"
        ordering = ["id"]

    @classmethod
    def table_name(cls) -> str:
        return "users"


class UserTokenModel(_PostgresCRUDMixin, models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        UserModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="user_id",
        db_index=True,
        related_name="tokens",
    )
    access = models.TextField()
    refresh = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_tokens"
        ordering = ["id"]

    @classmethod
    def table_name(cls) -> str:
        return "user_tokens"


class UserPermissionModel(_PostgresCRUDMixin, models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        UserModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column="user_id",
        db_index=True,
        related_name="permissions",
    )
    permission = models.CharField(max_length=100)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_permissions"
        ordering = ["id"]

    @classmethod
    def table_name(cls) -> str:
        return "user_permissions"


ICRUDDataModel.register(UserModel)
ICRUDDataModel.register(UserTokenModel)
ICRUDDataModel.register(UserPermissionModel)
