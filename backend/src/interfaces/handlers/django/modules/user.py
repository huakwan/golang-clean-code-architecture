from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import serializers, status
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from src.domain.entities.user import (
    UserEntity,
    UserLoginRequest,
    UserLogoutRequest,
    UserRefreshTokenRequest,
    UserRegisterRequest,
)
from src.domain.exceptions import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from src.interfaces.handlers.django.entities.filter import get_client_ip, parse_json_object
from src.interfaces.handlers.django.entities.response import error_response
from src.usecases.user.user_usecase import UserUsecase


class _StrictStringField(serializers.CharField):
    """String field that rejects non-string primitives (None, int, bool, list, dict)."""

    def to_internal_value(self, data: Any) -> str:
        if not isinstance(data, str):
            self.fail("invalid")
        return super().to_internal_value(data)


class UserRegisterSerializer(serializers.Serializer):
    email = _StrictStringField(max_length=255, allow_blank=False)
    password = _StrictStringField(max_length=255, allow_blank=False, trim_whitespace=False)
    first_name = _StrictStringField(max_length=150, allow_blank=False)
    last_name = _StrictStringField(max_length=150, allow_blank=False)


class UserLoginSerializer(serializers.Serializer):
    email = _StrictStringField(max_length=255, allow_blank=False)
    password = _StrictStringField(max_length=255, allow_blank=False, trim_whitespace=False)


class UserRefreshTokenSerializer(serializers.Serializer):
    refresh_token = _StrictStringField(allow_blank=False)


class UserLogoutSerializer(serializers.Serializer):
    refresh_token = _StrictStringField(allow_blank=False)


def _first_serializer_error(serializer: serializers.Serializer) -> str:
    for field_name, errors in serializer.errors.items():
        first = errors[0] if isinstance(errors, list) and errors else errors
        return f"{field_name}: {first}"
    return "invalid request body"


class _BaseUserView(APIView):
    user_usecase: UserUsecase | None = None
    usecase_provider: Callable[[], UserUsecase] | None = None

    def _get_usecase(self) -> UserUsecase:
        if self.user_usecase is not None:
            return self.user_usecase
        if self.usecase_provider is not None:
            return self.usecase_provider()
        raise RuntimeError("user_usecase is not configured")


class UserRegisterView(_BaseUserView):
    authentication_classes: list[type[BaseAuthentication]] = []
    permission_classes = [AllowAny]
    throttle_scope = "auth_register"

    @extend_schema(
        tags=["Users"],
        summary="Register User",
        request=UserRegisterSerializer,
        responses={201: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 409: OpenApiTypes.OBJECT},
    )
    def post(self, request: Request) -> Response:
        body = parse_json_object(request.data)
        if body is None:
            return error_response("users-001", "invalid request body", status.HTTP_400_BAD_REQUEST)

        serializer = UserRegisterSerializer(data=body)
        if not serializer.is_valid():
            return error_response(
                "users-001",
                _first_serializer_error(serializer),
                status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        dto = UserRegisterRequest(
            email=data["email"],
            password=data["password"],
            first_name=data["first_name"],
            last_name=data["last_name"],
        )
        try:
            user = self._get_usecase().register_user(dto, ip_address=get_client_ip(request))
        except ValidationError as exc:
            return error_response("users-001", str(exc), status.HTTP_400_BAD_REQUEST)
        except ConflictError as exc:
            return error_response("users-001", str(exc), status.HTTP_409_CONFLICT)

        return Response(user.to_dict(), status=status.HTTP_201_CREATED)


class UserLoginView(_BaseUserView):
    authentication_classes: list[type[BaseAuthentication]] = []
    permission_classes = [AllowAny]
    throttle_scope = "auth_login"

    @extend_schema(
        tags=["Users"],
        summary="Login User",
        request=UserLoginSerializer,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request: Request) -> Response:
        body = parse_json_object(request.data)
        if body is None:
            return error_response("users-002", "invalid request body", status.HTTP_400_BAD_REQUEST)

        serializer = UserLoginSerializer(data=body)
        if not serializer.is_valid():
            return error_response(
                "users-002",
                _first_serializer_error(serializer),
                status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        dto = UserLoginRequest(email=data["email"], password=data["password"])
        try:
            result = self._get_usecase().login(dto, ip_address=get_client_ip(request))
        except (AuthenticationError, ValidationError) as exc:
            return error_response("users-002", str(exc), status.HTTP_400_BAD_REQUEST)

        return Response(result.to_dict(), status=status.HTTP_200_OK)


class UserRefreshTokenView(_BaseUserView):
    authentication_classes: list[type[BaseAuthentication]] = []
    permission_classes = [AllowAny]
    throttle_scope = "auth_refresh"

    @extend_schema(
        tags=["Users"],
        summary="Refresh Access Token",
        request=UserRefreshTokenSerializer,
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request: Request) -> Response:
        body = parse_json_object(request.data)
        if body is None:
            return error_response(
                "users-003",
                "refresh_token is required",
                status.HTTP_400_BAD_REQUEST,
            )

        serializer = UserRefreshTokenSerializer(data=body)
        if not serializer.is_valid():
            return error_response(
                "users-003",
                _first_serializer_error(serializer),
                status.HTTP_400_BAD_REQUEST,
            )

        dto = UserRefreshTokenRequest(refresh_token=serializer.validated_data["refresh_token"])
        try:
            result = self._get_usecase().refresh_token(dto, ip_address=get_client_ip(request))
        except (AuthenticationError, NotFoundError) as exc:
            return error_response("users-003", str(exc), status.HTTP_400_BAD_REQUEST)

        return Response(result.to_dict(), status=status.HTTP_200_OK)


class UserLogoutView(_BaseUserView):
    authentication_classes: list[type[BaseAuthentication]] = []
    permission_classes = [AllowAny]
    throttle_scope = "auth_logout"

    @extend_schema(
        tags=["Users"],
        summary="Logout User",
        request=UserLogoutSerializer,
        responses={200: OpenApiTypes.NONE, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request: Request) -> Response | JsonResponse:
        body = parse_json_object(request.data)
        if body is None:
            return error_response(
                "users-004",
                "refresh_token is required",
                status.HTTP_400_BAD_REQUEST,
            )

        serializer = UserLogoutSerializer(data=body)
        if not serializer.is_valid():
            return error_response(
                "users-004",
                _first_serializer_error(serializer),
                status.HTTP_400_BAD_REQUEST,
            )

        dto = UserLogoutRequest(refresh_token=serializer.validated_data["refresh_token"])
        try:
            self._get_usecase().logout(dto, ip_address=get_client_ip(request))
        except AuthenticationError as exc:
            return error_response("users-004", str(exc), status.HTTP_400_BAD_REQUEST)

        # DRF's JSONRenderer emits an empty body for Response(None); JsonResponse preserves
        # the JSON `null` contract expected by the Go reference and frontend client.
        return JsonResponse(None, safe=False, status=status.HTTP_200_OK)


class UserProfileView(_BaseUserView):
    @extend_schema(
        tags=["Users"],
        summary="Get Current User Profile",
        responses={200: OpenApiTypes.OBJECT, 401: OpenApiTypes.OBJECT},
    )
    def get(self, request: Request) -> Response:
        entity = getattr(request.user, "entity", None)
        if isinstance(entity, UserEntity):
            payload = entity.to_dict()
            perm = getattr(request.user, "permission", None)
            payload["permission"] = perm.permission if perm is not None else None
            return Response(payload, status=status.HTTP_200_OK)

        try:
            user = self._get_usecase().get_user_profile(request.user.id)
        except NotFoundError as exc:
            return error_response("users-005", str(exc), status.HTTP_404_NOT_FOUND)

        payload = user.to_dict()
        payload["permission"] = None
        return Response(payload, status=status.HTTP_200_OK)
