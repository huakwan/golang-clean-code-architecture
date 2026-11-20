from __future__ import annotations

from collections.abc import Callable

from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import status
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from src.domain.entities.monitor import MonitorEntity


class MonitorHealthCheckView(APIView):
    authentication_classes: list[type[BaseAuthentication]] = []
    permission_classes = [AllowAny]
    monitor_provider: Callable[[], MonitorEntity] | None = None

    @extend_schema(
        tags=["Monitor"],
        summary="Health Check",
        description="Return application name and version.",
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request: Request) -> Response:
        if self.monitor_provider is None:
            raise RuntimeError("monitor_provider is not configured")
        entity = self.monitor_provider()
        return Response(entity.to_dict(), status=status.HTTP_200_OK)
