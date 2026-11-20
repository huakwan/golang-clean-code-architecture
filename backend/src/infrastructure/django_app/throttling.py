from __future__ import annotations

from rest_framework.request import Request
from rest_framework.throttling import ScopedRateThrottle

from src.interfaces.handlers.django.entities.filter import get_client_ip


class ClientIPScopedRateThrottle(ScopedRateThrottle):
    """Scoped rate limiter keyed by spoofing-resistant client IP."""

    def get_ident(self, request: Request) -> str:
        return get_client_ip(request)
