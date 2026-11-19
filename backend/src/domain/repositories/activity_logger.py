from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class IActivityLogger(ABC):
    """Decoupled audit logger contract for recording auth/system events."""

    @abstractmethod
    def record(
        self,
        *,
        user_id: int | None,
        action: str,
        resource: str,
        status: str,
        ip_address: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record an audit log entry."""
