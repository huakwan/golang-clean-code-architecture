from __future__ import annotations

from contextlib import AbstractContextManager

from django.db import IntegrityError, transaction

from src.domain.entities.user import (
    UserEntity,
    UserPermissionEntity,
    UserTokenEntity,
)
from src.domain.exceptions import ConflictError
from src.domain.repositories.user_repository import IUserRepository, StoredUserRecord
from src.infrastructure.database.postgres.models import (
    UserModel,
    UserPermissionModel,
    UserTokenModel,
)
from src.shared.utils import format_iso_datetime


def _to_user_entity(model: UserModel) -> UserEntity:
    return UserEntity(
        id=model.id,
        email=model.email,
        first_name=model.first_name,
        last_name=model.last_name,
        created_at=format_iso_datetime(model.created_at),
        updated_at=format_iso_datetime(model.updated_at),
    )


class PostgresUserRepository(IUserRepository):
    def atomic(self) -> AbstractContextManager[None]:
        return transaction.atomic()

    def get_user_by_email(self, email: str) -> StoredUserRecord | None:
        record = UserModel.objects.filter(email=email).first()
        if record is None:
            return None
        return StoredUserRecord(user=_to_user_entity(record), password_hash=record.password)

    def get_user_by_user_id(self, user_id: int) -> UserEntity | None:
        record = UserModel.objects.filter(id=user_id).first()
        if record is None:
            return None
        return _to_user_entity(record)

    def insert_user(
        self,
        email: str,
        password_hash: str,
        first_name: str,
        last_name: str,
    ) -> UserEntity:
        try:
            with transaction.atomic():
                record = UserModel.objects.create(
                    email=email,
                    password=password_hash,
                    first_name=first_name,
                    last_name=last_name,
                )
        except IntegrityError as exc:
            raise ConflictError("email already exists") from exc
        return _to_user_entity(record)

    def insert_user_permission(self, user_id: int, permission: str) -> UserPermissionEntity:
        record = UserPermissionModel.objects.create(user_id=user_id, permission=permission)
        return UserPermissionEntity(
            id=record.id,
            user_id=user_id,
            permission=record.permission,
            updated_at=format_iso_datetime(record.updated_at),
        )

    def upsert_oauth(self, user_id: int, access_token: str, refresh_token: str) -> UserTokenEntity:
        with transaction.atomic():
            UserTokenModel.objects.update_or_create(
                user_id=user_id,
                defaults={"access": access_token, "refresh": refresh_token},
            )
        return UserTokenEntity(access=access_token, refresh=refresh_token)

    def find_one_oauth_by_user_id(
        self,
        user_id: int,
        *,
        for_update: bool = False,
    ) -> UserTokenEntity | None:
        qs = UserTokenModel.objects.filter(user_id=user_id)
        if for_update:
            qs = qs.select_for_update()
        record = qs.first()
        if record is None:
            return None
        return UserTokenEntity(access=record.access, refresh=record.refresh)

    def find_oauth_by_user_id_and_access_token(
        self,
        user_id: int,
        access_token: str,
    ) -> UserTokenEntity | None:
        record = UserTokenModel.objects.filter(user_id=user_id, access=access_token).first()
        if record is None:
            return None
        return UserTokenEntity(access=record.access, refresh=record.refresh)

    def delete_oauth_by_user_id(self, user_id: int) -> None:
        UserTokenModel.objects.filter(user_id=user_id).delete()

    def get_user_permission_by_user_id(self, user_id: int) -> UserPermissionEntity | None:
        record = UserPermissionModel.objects.filter(user_id=user_id).first()
        if record is None:
            return None
        return UserPermissionEntity(
            id=record.id,
            user_id=record.user_id,
            permission=record.permission,
            updated_at=format_iso_datetime(record.updated_at),
        )
