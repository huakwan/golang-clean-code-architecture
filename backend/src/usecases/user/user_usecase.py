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
    UserTokenEntity,
)
from src.domain.exceptions import (
    AuthenticationError,
    ConflictError,
    DomainError,
    NotFoundError,
    ValidationError,
)
from src.domain.repositories.activity_logger import IActivityLogger
from src.domain.repositories.user_repository import IUserRepository
from src.shared.authentication.jwt_authentication import (
    ACCESS_TOKEN_SUBJECT,
    REFRESH_TOKEN_SUBJECT,
    JWTAuthenticator,
    hash_token,
    verify_token_hash,
)
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
        # Audit logging is intentionally non-fatal so auth flows survive log-sink outages.
        try:
            self._activity_logger.record(
                user_id=user_id,
                action=action,
                resource="users",
                status=status,
                ip_address=ip_address,
                metadata=metadata or {},
            )
        except (OSError, RuntimeError, DomainError):
            logger.warning("Failed to record activity log for action=%s", action, exc_info=True)

    def register_user(
        self,
        request: UserRegisterRequest,
        ip_address: str = "",
    ) -> UserEntity:
        normalized_email = request.normalized_email()
        first_name = request.first_name.strip()
        last_name = request.last_name.strip()

        if not request.is_valid_email():
            raise ValidationError("email pattern is invalid")
        if len(normalized_email) > 255:
            raise ValidationError("email must be at most 255 characters")
        if not request.password:
            raise ValidationError("password is required")
        if not first_name or not last_name:
            raise ValidationError("first_name and last_name are required")
        if len(first_name) > 150 or len(last_name) > 150:
            raise ValidationError("first_name and last_name must be at most 150 characters")

        if self._user_repo.get_user_by_email(normalized_email) is not None:
            raise ConflictError("email already exists")

        hashed = hash_password(request.password)
        with self._user_repo.atomic():
            user = self._user_repo.insert_user(
                email=normalized_email,
                password_hash=hashed,
                first_name=first_name,
                last_name=last_name,
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
        normalized_email = request.normalized_email()
        stored = self._user_repo.get_user_by_email(normalized_email)
        password_ok = verify_password(
            request.password,
            stored.password_hash if stored is not None else None,
        )
        if stored is None or not password_ok:
            self._log_activity(
                user_id=stored.user.id if stored is not None else None,
                action="USER_LOGIN",
                status="failed",
                ip_address=ip_address,
                metadata={"email": normalized_email},
            )
            raise AuthenticationError("password is invalid")

        claims = UserTokenClaimsEntity(id=stored.user.id)
        access_token = self._jwt_auth.create_access_token(claims)
        refresh_token = self._jwt_auth.create_refresh_token(claims)
        self._user_repo.upsert_oauth(
            stored.user.id,
            hash_token(access_token),
            hash_token(refresh_token),
        )

        self._log_activity(
            user_id=stored.user.id,
            action="USER_LOGIN",
            status="success",
            ip_address=ip_address,
            metadata={"email": stored.user.email},
        )
        return UserLoginResponse(
            user=stored.user,
            token=UserTokenEntity(access=access_token, refresh=refresh_token),
        )

    def refresh_token(
        self,
        request: UserRefreshTokenRequest,
        ip_address: str = "",
    ) -> UserLoginResponse:
        parsed = self._jwt_auth.parse_token(
            request.refresh_token,
            expected_sub=REFRESH_TOKEN_SUBJECT,
        )
        user_id = parsed.claims.id

        with self._user_repo.atomic():
            stored_token = self._user_repo.find_one_oauth_by_user_id(
                user_id,
                for_update=True,
            )
            if stored_token is None or not verify_token_hash(
                request.refresh_token,
                stored_token.refresh,
            ):
                raise AuthenticationError("user token not found")

            user = self._user_repo.get_user_by_user_id(user_id)
            if user is None:
                raise NotFoundError("user not found")

            claims = UserTokenClaimsEntity(id=user.id)
            new_access = self._jwt_auth.create_access_token(claims)
            repeated_refresh = self._jwt_auth.repeat_refresh_token(claims, parsed.exp)
            self._user_repo.upsert_oauth(
                user.id,
                hash_token(new_access),
                hash_token(repeated_refresh),
            )

        self._log_activity(
            user_id=user.id,
            action="USER_REFRESH_TOKEN",
            status="success",
            ip_address=ip_address,
        )
        return UserLoginResponse(
            user=user,
            token=UserTokenEntity(access=new_access, refresh=repeated_refresh),
        )

    def logout(
        self,
        request: UserLogoutRequest,
        ip_address: str = "",
    ) -> None:
        parsed = self._jwt_auth.parse_token(
            request.refresh_token,
            expected_sub=REFRESH_TOKEN_SUBJECT,
        )
        user_id = parsed.claims.id

        stored_token = self._user_repo.find_one_oauth_by_user_id(user_id)
        if stored_token is None or not verify_token_hash(
            request.refresh_token,
            stored_token.refresh,
        ):
            raise AuthenticationError("user token not found")

        self._user_repo.delete_oauth_by_user_id(user_id)
        self._log_activity(
            user_id=user_id,
            action="USER_LOGOUT",
            status="success",
            ip_address=ip_address,
        )

    def authenticate(self, access_token: str) -> tuple[UserEntity, UserPermissionEntity | None]:
        clean_token = access_token.strip()
        parsed = self._jwt_auth.parse_token(clean_token, expected_sub=ACCESS_TOKEN_SUBJECT)
        user_id = parsed.claims.id

        stored_token = self._user_repo.find_oauth_by_user_id_and_access_token(
            user_id,
            hash_token(clean_token),
        )
        if stored_token is None or not verify_token_hash(clean_token, stored_token.access):
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
