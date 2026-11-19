from __future__ import annotations

import re

_CAMEL_BOUNDARY = re.compile(r"(?<!^)(?=[A-Z])")


def convert_name_to_crud_slug(name: str) -> str:
    """Convert CamelCase or snake_case model/table names to kebab-case CRUD slugs."""
    snake = _CAMEL_BOUNDARY.sub("_", name).lower()
    return snake.replace("_", "-")
