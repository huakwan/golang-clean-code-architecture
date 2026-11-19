from __future__ import annotations

from django.http import JsonResponse
from drf_spectacular.utils import OpenApiTypes, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from src.domain.entities.user import (
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
from src.infrastructure.container import get_container
from src.infrastructure.django_app.authentication import CustomJWTAuthentication
from src.interfaces.handlers.django.entities.filter import get_client_ip, parse_json_object
from src.interfaces.handlers.django.entities.response import error_response
from src.usecases.user.user_usecase import UserUsecase


class _BaseUserView(APIView):
    user_usecase: UserUsecase | None = None

    def _get_usecase(self) -> UserUsecase:
        return self.user_usecase or get_container().user_usecase


class UserRegisterView(_BaseUserView):
    authentication_classes: list[type] = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Users"],
        summary="Register User",
        request=inline_serializer(
            name="UserRegisterPayload",
            fields={
                "email": serializers.EmailField(),
                "password": serializers.CharField(),
                "first_name": serializers.CharField(),
                "last_name": serializers.CharField(),
            },
        ),
        responses={201: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 409: OpenApiTypes.OBJECT},
    )
    def post(self, request: Request) -> Response:
        body = parse_json_object(request.data)
        if body is None:
            return error_response("users-001", "invalid request body", status.HTTP_400_BAD_REQUEST)

        dto = UserRegisterRequest(
            email=str(body.get("email", "")).strip(),
            password=str(body.get("password", "")),
            first_name=str(body.get("first_name", "")).strip(),
            last_name=str(body.get("last_name", "")).strip(),
        )
        try:
            user = self._get_usecase().register_user(dto, ip_address=get_client_ip(request))
        except ValidationError as exc:
            return error_response("users-001", str(exc), status.HTTP_400_BAD_REQUEST)
        except ConflictError as exc:
            return error_response("users-001", str(exc), status.HTTP_409_CONFLICT)

        return Response(user.to_dict(), status=status.HTTP_201_CREATED)


class UserLoginView(_BaseUserView):
    authentication_classes: list[type] = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Users"],
        summary="Login User",
        request=inline_serializer(
            name="UserLoginPayload",
            fields={
                "email": serializers.EmailField(),
                "password": serializers.CharField(),
            },
        ),
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request: Request) -> Response:
        body = parse_json_object(request.data)
        if body is None:
            return error_response("users-002", "invalid request body", status.HTTP_400_BAD_REQUEST)

        dto = UserLoginRequest(
            email=str(body.get("email", "")).strip(),
            password=str(body.get("password", "")),
        )
        try:
            result = self._get_usecase().login(dto, ip_address=get_client_ip(request))
        except (AuthenticationError, ValidationError) as exc:
            return error_response("users-002", str(exc), status.HTTP_400_BAD_REQUEST)

        return Response(result.to_dict(), status=status.HTTP_200_OK)


class UserRefreshTokenView(_BaseUserView):
    authentication_classes: list[type] = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Users"],
        summary="Refresh Access Token",
        request=inline_serializer(
            name="UserRefreshTokenPayload",
            fields={"refresh_token": serializers.CharField()},
        ),
        responses={200: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request: Request) -> Response:
        body = parse_json_object(request.data)
        if body is None or not body.get("refresh_token"):
            return error_response(
                "users-003",
                "refresh_token is required",
                status.HTTP_400_BAD_REQUEST,
            )

        dto = UserRefreshTokenRequest(refresh_token=str(body["refresh_token"]))
        try:
            result = self._get_usecase().refresh_token(dto, ip_address=get_client_ip(request))
        except (AuthenticationError, NotFoundError) as exc:
            return error_response("users-003", str(exc), status.HTTP_400_BAD_REQUEST)

        return Response(result.to_dict(), status=status.HTTP_200_OK)


class UserLogoutView(_BaseUserView):
    authentication_classes: list[type] = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Users"],
        summary="Logout User",
        request=inline_serializer(
            name="UserLogoutPayload",
            fields={"refresh_token": serializers.CharField()},
        ),
        responses={200: OpenApiTypes.NONE, 400: OpenApiTypes.OBJECT},
    )
    def post(self, request: Request) -> Response | JsonResponse:
        body = parse_json_object(request.data)
        if body is None or not body.get("refresh_token"):
            return error_response(
                "users-004",
                "refresh_token is required",
                status.HTTP_400_BAD_REQUEST,
            )

        dto = UserLogoutRequest(refresh_token=str(body["refresh_token"]))
        try:
            self._get_usecase().logout(dto, ip_address=get_client_ip(request))
        except AuthenticationError as exc:
            return error_response("users-004", str(exc), status.HTTP_400_BAD_REQUEST)

        return JsonResponse(None, safe=False, status=status.HTTP_200_OK)


class UserProfileView(_BaseUserView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Users"],
        summary="Get Current User Profile",
        responses={200: OpenApiTypes.OBJECT, 401: OpenApiTypes.OBJECT},
    )
    def get(self, request: Request) -> Response:
        try:
            user = self._get_usecase().get_user_profile(request.user.id)
        except NotFoundError as exc:
            return error_response("users-005", str(exc), status.HTTP_404_NOT_FOUND)

        return Response(user.to_dict(), status=status.HTTP_200_OK)
