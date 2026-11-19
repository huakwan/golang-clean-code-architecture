from __future__ import annotations

from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from src.config.env_config import AppConfig
from src.domain.entities.monitor import MonitorEntity
from src.infrastructure.container import get_container


class MonitorHealthCheckView(APIView):
    authentication_classes: list[type] = []
    permission_classes = [AllowAny]
    app_config: AppConfig | None = None

    def _get_config(self) -> AppConfig:
        return self.app_config or get_container().config

    @extend_schema(
        tags=["Monitor"],
        summary="Health Check",
        description="Return application name and version.",
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request: Request) -> Response:
        cfg = self._get_config()
        entity = MonitorEntity(name=cfg.name, version=cfg.version)
        return Response(entity.to_dict(), status=status.HTTP_200_OK)
