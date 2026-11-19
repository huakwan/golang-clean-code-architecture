from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from src.domain.entities.user import UserEntity, UserPermissionEntity
from src.domain.exceptions import AuthenticationError
from src.infrastructure.container import get_container
from src.usecases.user.user_usecase import UserUsecase


@dataclass
class AuthenticatedUser:
    """DRF-compatible wrapper around domain UserEntity and UserPermissionEntity."""

    entity: UserEntity
    permission: UserPermissionEntity | None = None

    @property
    def id(self) -> int:
        return self.entity.id

    @property
    def is_authenticated(self) -> bool:
        return True


class CustomJWTAuthentication(BaseAuthentication):
    """DRF Authentication class delegating JWT + session validation to UserUsecase."""

    keyword = "Bearer"

    def __init__(self, user_usecase: UserUsecase | None = None) -> None:
        self._user_usecase = user_usecase

    def _get_user_usecase(self) -> UserUsecase:
        return self._user_usecase or get_container().user_usecase

    def authenticate(self, request: Request) -> tuple[AuthenticatedUser, str] | None:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header:
            return None

        if not auth_header.startswith("Bearer "):
            raise AuthenticationFailed("token format is invalid")

        try:
            user_entity, permission = self._get_user_usecase().authenticate(auth_header)
        except AuthenticationError as exc:
            raise AuthenticationFailed(str(exc)) from exc

        token = auth_header.removeprefix("Bearer ").strip()
        return AuthenticatedUser(entity=user_entity, permission=permission), token

    def authenticate_header(self, request: Request) -> str:
        return self.keyword


class CustomJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "src.infrastructure.django_app.authentication.CustomJWTAuthentication"
    name = "BearerAuth"

    def get_security_definition(self, auto_schema: Any) -> dict[str, Any]:
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
