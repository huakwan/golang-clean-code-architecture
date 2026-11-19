from __future__ import annotations

import pytest

from src.shared.crud.converter import convert_name_to_crud_slug


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("users", "users"),
        ("user_tokens", "user-tokens"),
        ("user_permissions", "user-permissions"),
        ("activity_logs", "activity-logs"),
        ("UserModel", "user-model"),
        ("UserTokenModel", "user-token-model"),
        ("ActivityLogDocument", "activity-log-document"),
    ],
)
def test_convert_name_to_crud_slug(raw: str, expected: str) -> None:
    assert convert_name_to_crud_slug(raw) == expected
