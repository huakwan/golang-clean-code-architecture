from __future__ import annotations

from collections.abc import Callable

from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from src.interfaces.handlers.django.entities.filter import (
    parse_json_object,
    parse_pagination_params,
)
from src.interfaces.handlers.django.entities.response import error_response
from src.usecases.crud.crud_usecase import CrudUsecase


class _BaseCrudView(APIView):
    crud_usecase: CrudUsecase | None = None
    usecase_provider: Callable[[], CrudUsecase] | None = None

    def _get_usecase(self) -> CrudUsecase:
        if self.crud_usecase is not None:
            return self.crud_usecase
        if self.usecase_provider is not None:
            return self.usecase_provider()
        raise RuntimeError("crud_usecase is not configured")

    def _get_permission(self, request: Request) -> str | None:
        user = getattr(request, "user", None)
        perm = getattr(user, "permission", None)
        return perm.permission if perm is not None else None


class CrudModelListView(_BaseCrudView):
    @extend_schema(
        tags=["Dynamic CRUD"],
        summary="List Registered Dynamic CRUD Models",
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request: Request) -> Response:
        permission = self._get_permission(request)
        models_info = [
            item.to_dict() for item in self._get_usecase().list_models(permission=permission)
        ]
        return Response(models_info, status=status.HTTP_200_OK)


class CrudDescribeView(_BaseCrudView):
    @extend_schema(
        tags=["Dynamic CRUD"],
        summary="Describe Entity Avro Schema",
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def get(self, request: Request, entity_model_slug: str) -> Response:
        schema = self._get_usecase().describe(
            entity_model_slug,
            permission=self._get_permission(request),
        )
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
        result = self._get_usecase().list_records(
            entity_model_slug,
            page=page,
            page_size=page_size,
            filters=filters,
            permission=self._get_permission(request),
        )
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
        result = self._get_usecase().create(
            entity_model_slug,
            body,
            permission=self._get_permission(request),
        )
        return Response(result.to_dict(), status=status.HTTP_201_CREATED)


class CrudDetailView(_BaseCrudView):
    @extend_schema(
        tags=["Dynamic CRUD"],
        summary="Retrieve Entity Record by ID",
        responses={200: OpenApiTypes.OBJECT, 404: OpenApiTypes.OBJECT},
    )
    def get(self, request: Request, entity_model_slug: str, record_id: str) -> Response:
        result = self._get_usecase().retrieve(
            entity_model_slug,
            record_id,
            permission=self._get_permission(request),
        )
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
        result = self._get_usecase().update(
            entity_model_slug,
            record_id,
            body,
            permission=self._get_permission(request),
        )
        return Response(result.to_dict(), status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Dynamic CRUD"],
        summary="Delete Entity Record by ID",
        responses={204: OpenApiTypes.NONE, 404: OpenApiTypes.OBJECT, 405: OpenApiTypes.OBJECT},
    )
    def delete(self, request: Request, entity_model_slug: str, record_id: str) -> Response:
        self._get_usecase().delete(
            entity_model_slug,
            record_id,
            permission=self._get_permission(request),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
