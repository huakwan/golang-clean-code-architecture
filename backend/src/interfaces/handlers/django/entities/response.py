from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
    MethodNotAllowed,
    NotAuthenticated,
    NotFound,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


def error_response(
    trace_id: str,
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
) -> Response:
    return Response(
        {"trace_id": trace_id, "message": message},
        status=status_code,
    )


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    if isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
        detail = str(exc.detail) if hasattr(exc, "detail") else str(exc)
        return error_response("middleware-002", detail, status.HTTP_401_UNAUTHORIZED)

    if isinstance(exc, NotFound):
        detail = str(exc.detail) if hasattr(exc, "detail") else "router not found"
        return error_response("middleware-001", detail, status.HTTP_404_NOT_FOUND)

    if isinstance(exc, MethodNotAllowed):
        detail = str(exc.detail) if hasattr(exc, "detail") else "method not allowed"
        return error_response("middleware-003", detail, status.HTTP_405_METHOD_NOT_ALLOWED)

    response = drf_exception_handler(exc, context)
    if response is not None:
        if isinstance(response.data, dict):
            detail = response.data.get("detail", str(response.data))
        else:
            detail = str(response.data)
        return error_response("error", str(detail), response.status_code)

    return None
