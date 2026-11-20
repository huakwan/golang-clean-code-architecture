from __future__ import annotations

import re

_ACRONYM_BOUNDARY = re.compile(r"([A-Z]+)([A-Z][a-z])")
_CAMEL_BOUNDARY = re.compile(r"([a-z0-9])([A-Z])")


def convert_name_to_crud_slug(name: str) -> str:
    """Convert CamelCase or snake_case model/table names to kebab-case CRUD slugs."""
    step1 = _ACRONYM_BOUNDARY.sub(r"\1_\2", name)
    snake = _CAMEL_BOUNDARY.sub(r"\1_\2", step1).lower()
    return snake.replace("_", "-")
