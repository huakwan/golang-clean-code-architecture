from __future__ import annotations

import ipaddress
from collections.abc import Mapping
from typing import Any

from django.conf import settings
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


def _is_trusted_proxy(ip_str: str, trusted_proxies: tuple[str, ...]) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    for entry in trusted_proxies:
        try:
            if ip in ipaddress.ip_network(entry, strict=False):
                return True
        except ValueError:
            continue
    return False


def get_client_ip(
    request: Request,
    *,
    trusted_proxies: tuple[str, ...] | None = None,
) -> str:
    remote_addr = str(request.META.get("REMOTE_ADDR", "")).strip()
    proxies = (
        trusted_proxies
        if trusted_proxies is not None
        else tuple(getattr(settings, "TRUSTED_PROXIES", ()))
    )
    if not proxies or not _is_trusted_proxy(remote_addr, proxies):
        return remote_addr

    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if not forwarded:
        return remote_addr

    hops = [hop.strip() for hop in str(forwarded).split(",") if hop.strip()]
    for hop in reversed(hops):
        if not _is_trusted_proxy(hop, proxies):
            return hop
    return hops[0] if hops else remote_addr
