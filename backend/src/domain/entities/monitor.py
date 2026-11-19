from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class MonitorEntity:
    name: str
    version: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
