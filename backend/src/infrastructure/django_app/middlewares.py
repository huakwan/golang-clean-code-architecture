from __future__ import annotations

import logging
import re
import time
import uuid
from collections.abc import Callable

from django.http import HttpRequest, HttpResponse, JsonResponse

logger = logging.getLogger("api.request")

_SAFE_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def _resolve_request_id(request: HttpRequest) -> str:
    incoming = str(request.META.get("HTTP_X_REQUEST_ID", "")).strip()
    if incoming and _SAFE_REQUEST_ID_RE.match(incoming):
        return incoming
    return uuid.uuid4().hex


def _sanitize_log_path(path: str) -> str:
    return path.replace("\r", "").replace("\n", "")


class RequestLoggerMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = _resolve_request_id(request)
        request.request_id = request_id
        safe_path = _sanitize_log_path(request.path)
        start = time.monotonic()
        try:
            response = self.get_response(request)
        except Exception:
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.exception(
                "[req=%s] %s %s -> 500 (%.1fms)",
                request_id,
                request.method,
                safe_path,
                elapsed_ms,
            )
            raise

        elapsed_ms = (time.monotonic() - start) * 1000
        response["X-Request-ID"] = request_id
        logger.info(
            "[req=%s] %s %s -> %s (%.1fms)",
            request_id,
            request.method,
            safe_path,
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
