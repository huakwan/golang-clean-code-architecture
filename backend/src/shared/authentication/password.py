from __future__ import annotations

from functools import lru_cache

import bcrypt


def hash_password(plain_password: str, rounds: int = 10) -> str:
    salt = bcrypt.gensalt(rounds=rounds)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


@lru_cache(maxsize=1)
def _get_dummy_hash() -> str:
    return hash_password("timing-protection-dummy-password")


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    if not hashed_password:
        bcrypt.checkpw(plain_password.encode("utf-8"), _get_dummy_hash().encode("utf-8"))
        return False
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except ValueError:
        return False
