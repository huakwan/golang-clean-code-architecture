from __future__ import annotations

import logging
from typing import Any

from src.domain.entities.user import (
    UserEntity,
    UserLoginRequest,
    UserLoginResponse,
    UserLogoutRequest,
    UserPermissionEntity,
    UserRefreshTokenRequest,
    UserRegisterRequest,
    UserTokenClaimsEntity,
)
from src.domain.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from src.domain.repositories.activity_logger import IActivityLogger
from src.domain.repositories.user_repository import IUserRepository
from src.shared.authentication.jwt_authentication import JWTAuthenticator
from src.shared.authentication.password import hash_password, verify_password

logger = logging.getLogger(__name__)


class UserUsecase:
    """Application business logic for user management and JWT authentication."""

    def __init__(
        self,
        *,
        user_repo: IUserRepository,
        jwt_auth: JWTAuthenticator,
        activity_logger: IActivityLogger | None = None,
    ) -> None:
        self._user_repo = user_repo
        self._jwt_auth = jwt_auth
        self._activity_logger = activity_logger

    def _log_activity(
        self,
        *,
        user_id: int | None,
        action: str,
        status: str,
        ip_address: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if self._activity_logger is None:
            return
        try:
            self._activity_logger.record(
                user_id=user_id,
                action=action,
                resource="users",
                status=status,
                ip_address=ip_address,
                metadata=metadata or {},
            )
        except (OSError, RuntimeError):
            logger.warning("Failed to record activity log for action=%s", action, exc_info=True)

    def register_user(
        self,
        request: UserRegisterRequest,
        ip_address: str = "",
    ) -> UserEntity:
        if not request.is_valid_email():
            raise ValidationError("email pattern is invalid")
        if not request.password:
            raise ValidationError("password is required")
        if not request.first_name or not request.last_name:
            raise ValidationError("first_name and last_name are required")

        if self._user_repo.get_user_by_email(request.email) is not None:
            raise ConflictError("email already exists")

        hashed = hash_password(request.password)
        user = self._user_repo.insert_user(
            email=request.email,
            password_hash=hashed,
            first_name=request.first_name,
            last_name=request.last_name,
        )
        self._user_repo.insert_user_permission(user.id, "user")
        self._log_activity(
            user_id=user.id,
            action="USER_REGISTER",
            status="success",
            ip_address=ip_address,
            metadata={"email": user.email},
        )
        return user

    def login(
        self,
        request: UserLoginRequest,
        ip_address: str = "",
    ) -> UserLoginResponse:
        stored = self._user_repo.get_user_by_email(request.email)
        if stored is None or not verify_password(request.password, stored.password_hash):
            self._log_activity(
                user_id=stored.user.id if stored is not None else None,
                action="USER_LOGIN",
                status="failed",
                ip_address=ip_address,
                metadata={"email": request.email},
            )
            raise AuthenticationError("password is invalid")

        claims = UserTokenClaimsEntity(id=stored.user.id)
        access_token = self._jwt_auth.create_access_token(claims)
        refresh_token = self._jwt_auth.create_refresh_token(claims)
        token_entity = self._user_repo.upsert_oauth(stored.user.id, access_token, refresh_token)

        self._log_activity(
            user_id=stored.user.id,
            action="USER_LOGIN",
            status="success",
            ip_address=ip_address,
            metadata={"email": stored.user.email},
        )
        return UserLoginResponse(user=stored.user, token=token_entity)

    def refresh_token(
        self,
        request: UserRefreshTokenRequest,
        ip_address: str = "",
    ) -> UserLoginResponse:
        parsed = self._jwt_auth.parse_token(request.refresh_token)
        user_id = parsed.claims.id

        stored_token = self._user_repo.find_one_oauth_by_user_id(user_id)
        if stored_token is None or stored_token.refresh != request.refresh_token:
            raise AuthenticationError("user token not found")

        user = self._user_repo.get_user_by_user_id(user_id)
        if user is None:
            raise NotFoundError("user not found")

        claims = UserTokenClaimsEntity(id=user.id)
        new_access = self._jwt_auth.create_access_token(claims)
        repeated_refresh = self._jwt_auth.repeat_refresh_token(claims, parsed.exp)
        token_entity = self._user_repo.upsert_oauth(user.id, new_access, repeated_refresh)

        self._log_activity(
            user_id=user.id,
            action="USER_REFRESH_TOKEN",
            status="success",
            ip_address=ip_address,
        )
        return UserLoginResponse(user=user, token=token_entity)

    def logout(
        self,
        request: UserLogoutRequest,
        ip_address: str = "",
    ) -> None:
        parsed = self._jwt_auth.parse_token(request.refresh_token)
        user_id = parsed.claims.id

        stored_token = self._user_repo.find_one_oauth_by_user_id(user_id)
        if stored_token is None or stored_token.refresh != request.refresh_token:
            raise AuthenticationError("user token not found")

        self._user_repo.delete_oauth_by_user_id(user_id)
        self._log_activity(
            user_id=user_id,
            action="USER_LOGOUT",
            status="success",
            ip_address=ip_address,
        )

    def authenticate(self, raw_token: str) -> tuple[UserEntity, UserPermissionEntity | None]:
        clean_token = raw_token.removeprefix("Bearer ").strip()
        parsed = self._jwt_auth.parse_token(clean_token)
        user_id = parsed.claims.id

        stored_token = self._user_repo.find_oauth_by_user_id_and_access_token(
            user_id,
            clean_token,
        )
        if stored_token is None:
            raise AuthenticationError("user token not found")

        user = self._user_repo.get_user_by_user_id(user_id)
        if user is None:
            raise AuthenticationError("user not found")

        permission = self._user_repo.get_user_permission_by_user_id(user_id)
        return user, permission

    def get_user_profile(self, user_id: int) -> UserEntity:
        user = self._user_repo.get_user_by_user_id(user_id)
        if user is None:
            raise NotFoundError("user not found")
        return user
