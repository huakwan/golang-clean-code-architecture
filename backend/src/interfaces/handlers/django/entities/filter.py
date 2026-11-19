from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from rest_framework.request import Request


def parse_pagination_params(
    query_params: Mapping[str, Any],
) -> tuple[int, int, dict[str, Any] | None]:
    raw_page = query_params.get("_page", "1")
    raw_page_size = query_params.get("_pageSize", "10")

    try:
        page = int(raw_page)
    except (TypeError, ValueError):
        page = 1

    try:
        page_size = int(raw_page_size)
    except (TypeError, ValueError):
        page_size = 10

    filters = {
        key: value
        for key, value in query_params.items()
        if key not in ("_page", "_pageSize") and value != ""
    }
    return page, page_size, filters or None


def parse_json_object(data: Any) -> dict[str, Any] | None:
    """Return a shallow dict copy if request payload is a JSON object, else None."""
    if not isinstance(data, dict):
        return None
    return dict(data)


def get_client_ip(request: Request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return str(forwarded).split(",")[0].strip()
    return str(request.META.get("REMOTE_ADDR", ""))
