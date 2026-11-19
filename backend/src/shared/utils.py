from __future__ import annotations

from datetime import date, datetime


def format_iso_datetime(value: datetime | date | None) -> str:
    """Format a datetime or date to ISO-8601 (UTC 'Z' suffix for timezone-aware UTC)."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    return value.isoformat()
