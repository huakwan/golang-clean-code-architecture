from __future__ import annotations

import logging
import time
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse, JsonResponse

logger = logging.getLogger("api.request")


class RequestLoggerMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        start = time.monotonic()
        response = self.get_response(request)
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.info(
            "%s %s -> %s (%.1fms)",
            request.method,
            request.path,
            response.status_code,
            elapsed_ms,
        )
        return response


class JSON404Middleware:
    """Convert non-JSON 404 responses into standardized API error JSON."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        content_type = response.get("Content-Type", "")
        if response.status_code == 404 and "application/json" not in content_type:
            return JsonResponse(
                {"trace_id": "middleware-001", "message": "router not found"},
                status=404,
            )
        return response
