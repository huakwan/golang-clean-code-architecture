from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from src.config.crud_models import list_registered_models
from src.domain.exceptions import (
    ConflictError,
    NotFoundError,
    OperationNotAllowedError,
    ValidationError,
)
from src.infrastructure.container import get_container
from src.infrastructure.django_app.authentication import CustomJWTAuthentication
from src.interfaces.handlers.django.entities.filter import (
    parse_json_object,
    parse_pagination_params,
)
from src.interfaces.handlers.django.entities.response import error_response
from src.usecases.crud.crud_usecase import CrudUsecase


def _handle_crud_error(exc: Exception) -> Response:
    if isinstance(exc, OperationNotAllowedError):
        return error_response("crud-405", str(exc), status.HTTP_405_METHOD_NOT_ALLOWED)
    if isinstance(exc, NotFoundError):
        return error_response("error", str(exc), status.HTTP_404_NOT_FOUND)
    if isinstance(exc, ConflictError):
        return error_response("error", str(exc), status.HTTP_409_CONFLICT)
    if isinstance(exc, ValidationError):
        return error_response("error", str(exc), status.HTTP_400_BAD_REQUEST)
    return error_response("error", "internal server error", status.HTTP_500_INTERNAL_SERVER_ERROR)


class _BaseCrudView(APIView):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    crud_usecase: CrudUsecase | None = None

    def _get_usecase(self) -> CrudUsecase:
        return self.crud_usecase or get_container().crud_usecase


class CrudModelListView(_BaseCrudView):
    @extend_schema(
        tags=["Dynamic CRUD"],
        summary="List Registered Dynamic CRUD Models",
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request: Request) -> Response:
        models_info = [item.to_dict() for item in list_registered_models()]
        return Response(models_info, status=status.HTTP_200_OK)


class CrudDescribeView(_BaseCrudView):
    @extend_schema(
        tags=["Dynamic CRUD"],
        summary="Describe Entity Avro Schema",
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def get(self, request: Request, entity_model_slug: str) -> Response:
        try:
            schema = self._get_usecase().describe(entity_model_slug)
        except (NotFoundError, ValidationError, OperationNotAllowedError) as exc:
            return _handle_crud_error(exc)
        return Response(schema, status=status.HTTP_200_OK)


class CrudListCreateView(_BaseCrudView):
    @extend_schema(
        tags=["Dynamic CRUD"],
        summary="List Entity Records (Paginated)",
        parameters=[
            OpenApiParameter("_page", OpenApiTypes.INT, description="Page number (default 1)"),
            OpenApiParameter(
                "_pageSize",
                OpenApiTypes.INT,
                description="Page size (default 10, max 1000)",
            ),
        ],
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request: Request, entity_model_slug: str) -> Response:
        page, page_size, filters = parse_pagination_params(request.query_params)
        try:
            result = self._get_usecase().list_records(
                entity_model_slug,
                page=page,
                page_size=page_size,
                filters=filters,
            )
        except (NotFoundError, ValidationError, OperationNotAllowedError) as exc:
            return _handle_crud_error(exc)
        return Response(result.to_dict(), status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Dynamic CRUD"],
        summary="Create Entity Record",
        request=OpenApiTypes.OBJECT,
        responses={201: OpenApiTypes.OBJECT, 400: OpenApiTypes.OBJECT, 405: OpenApiTypes.OBJECT},
    )
    def post(self, request: Request, entity_model_slug: str) -> Response:
        body = parse_json_object(request.data)
        if body is None:
            return error_response("error", "invalid request body", status.HTTP_400_BAD_REQUEST)
        try:
            result = self._get_usecase().create(entity_model_slug, body)
        except (NotFoundError, ValidationError, ConflictError, OperationNotAllowedError) as exc:
            return _handle_crud_error(exc)
        return Response(result.to_dict(), status=status.HTTP_201_CREATED)


class CrudDetailView(_BaseCrudView):
    @extend_schema(
        tags=["Dynamic CRUD"],
        summary="Retrieve Entity Record by ID",
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def get(self, request: Request, entity_model_slug: str, record_id: str) -> Response:
        try:
            result = self._get_usecase().retrieve(entity_model_slug, record_id)
        except (NotFoundError, ValidationError, OperationNotAllowedError) as exc:
            return _handle_crud_error(exc)
        return Response(result.to_dict(), status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Dynamic CRUD"],
        summary="Update Entity Record by ID",
        request=OpenApiTypes.OBJECT,
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT, 405: OpenApiTypes.OBJECT},
    )
    def put(self, request: Request, entity_model_slug: str, record_id: str) -> Response:
        body = parse_json_object(request.data)
        if body is None:
            return error_response("error", "invalid request body", status.HTTP_400_BAD_REQUEST)
        try:
            result = self._get_usecase().update(entity_model_slug, record_id, body)
        except (NotFoundError, ValidationError, ConflictError, OperationNotAllowedError) as exc:
            return _handle_crud_error(exc)
        return Response(result.to_dict(), status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Dynamic CRUD"],
        summary="Delete Entity Record by ID",
        responses={204: OpenApiTypes.NONE, 404: OpenApiTypes.OBJECT, 405: OpenApiTypes.OBJECT},
    )
    def delete(self, request: Request, entity_model_slug: str, record_id: str) -> Response:
        try:
            self._get_usecase().delete(entity_model_slug, record_id)
        except (NotFoundError, ValidationError, OperationNotAllowedError) as exc:
            return _handle_crud_error(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)
