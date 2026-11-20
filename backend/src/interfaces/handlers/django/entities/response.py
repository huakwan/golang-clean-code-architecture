from __future__ import annotations

import logging
import math
from typing import Any

from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import (
    AuthenticationFailed,
    MethodNotAllowed,
    NotAuthenticated,
    NotFound,
    Throttled,
)
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from src.domain.exceptions import (
    ConflictError,
    DatabaseError,
    DomainError,
    NotFoundError,
    OperationNotAllowedError,
    ValidationError,
)

logger = logging.getLogger(__name__)


def error_response(
    trace_id: str,
    message: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
) -> Response:
    return Response(
        {"trace_id": trace_id, "message": message},
        status=status_code,
    )


def _handle_domain_error(exc: DomainError) -> Response:
    if isinstance(exc, OperationNotAllowedError):
        return error_response("crud-405", str(exc), status.HTTP_405_METHOD_NOT_ALLOWED)
    if isinstance(exc, NotFoundError):
        return error_response("error", str(exc), status.HTTP_404_NOT_FOUND)
    if isinstance(exc, ConflictError):
        return error_response("error", str(exc), status.HTTP_409_CONFLICT)
    if isinstance(exc, ValidationError):
        return error_response("error", str(exc), status.HTTP_400_BAD_REQUEST)
    if isinstance(exc, DatabaseError):
        return error_response(
            "crud-503",
            "database service unavailable",
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return error_response("error", "internal server error", status.HTTP_500_INTERNAL_SERVER_ERROR)


def custom_exception_handler(exc: Exception, context: dict[str, Any]) -> Response | None:
    if isinstance(exc, DomainError):
        return _handle_domain_error(exc)

    if isinstance(exc, (AuthenticationFailed, NotAuthenticated)):
        detail = str(exc.detail) if hasattr(exc, "detail") else str(exc)
        return error_response("middleware-002", detail, status.HTTP_401_UNAUTHORIZED)

    if isinstance(exc, NotFound):
        detail = str(exc.detail) if hasattr(exc, "detail") else "router not found"
        return error_response("middleware-001", detail, status.HTTP_404_NOT_FOUND)

    if isinstance(exc, MethodNotAllowed):
        detail = str(exc.detail) if hasattr(exc, "detail") else "method not allowed"
        return error_response("middleware-003", detail, status.HTTP_405_METHOD_NOT_ALLOWED)

    if isinstance(exc, Throttled):
        detail = str(exc.detail) if hasattr(exc, "detail") else "request was throttled"
        resp = error_response("middleware-004", detail, status.HTTP_429_TOO_MANY_REQUESTS)
        if exc.wait is not None:
            resp["Retry-After"] = str(math.ceil(exc.wait))
        return resp

    response = drf_exception_handler(exc, context)
    if response is not None:
        if isinstance(response.data, dict):
            detail = response.data.get("detail", str(response.data))
        else:
            detail = str(response.data)
        return error_response("error", str(detail), response.status_code)

    if not settings.DEBUG:
        logger.exception("Unhandled API exception")
        return error_response(
            "error",
            "internal server error",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return None
