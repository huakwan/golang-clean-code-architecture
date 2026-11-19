from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from src.domain.entities.user import (
    UserEntity,
    UserPermissionEntity,
    UserTokenEntity,
)


@dataclass(frozen=True)
class StoredUserRecord:
    """Internal repository record pairing a UserEntity with its bcrypt password hash."""

    user: UserEntity
    password_hash: str


class IUserRepository(ABC):
    @abstractmethod
    def get_user_by_email(self, email: str) -> StoredUserRecord | None:
        """Fetch user and password hash by email, or None if not found."""

    @abstractmethod
    def get_user_by_user_id(self, user_id: int) -> UserEntity | None:
        """Fetch user by primary key, or None if not found."""

    @abstractmethod
    def insert_user(
        self,
        email: str,
        password_hash: str,
        first_name: str,
        last_name: str,
    ) -> UserEntity:
        """Persist a new user and return the created UserEntity."""

    @abstractmethod
    def insert_user_permission(self, user_id: int, permission: str) -> UserPermissionEntity:
        """Persist a permission record for the given user."""

    @abstractmethod
    def upsert_oauth(self, user_id: int, access_token: str, refresh_token: str) -> UserTokenEntity:
        """Insert or update the active token pair for a user."""

    @abstractmethod
    def find_one_oauth_by_user_id(self, user_id: int) -> UserTokenEntity | None:
        """Fetch the stored token pair for a user, or None if not found."""

    @abstractmethod
    def find_oauth_by_user_id_and_access_token(
        self,
        user_id: int,
        access_token: str,
    ) -> UserTokenEntity | None:
        """Verify that the access token matches the user's active session."""

    @abstractmethod
    def delete_oauth_by_user_id(self, user_id: int) -> None:
        """Revoke all active OAuth tokens for a user."""

    @abstractmethod
    def get_user_permission_by_user_id(self, user_id: int) -> UserPermissionEntity | None:
        """Fetch the user's permission record, or None if absent."""
