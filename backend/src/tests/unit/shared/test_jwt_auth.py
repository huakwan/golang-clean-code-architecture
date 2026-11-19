from __future__ import annotations

import time

import jwt
import pytest

from src.domain.entities.user import UserTokenClaimsEntity
from src.domain.exceptions import AuthenticationError
from src.shared.authentication.jwt_authentication import JWTAuthenticator
from src.shared.authentication.password import hash_password, verify_password


def _make_auth(access_exp: int = 3600, refresh_exp: int = 86400) -> JWTAuthenticator:
    return JWTAuthenticator(
        secret_key="test-secret-key-at-least-32-bytes-long",
        app_name="PYTHON DJANGO CLEAN API",
        access_expires=access_exp,
        refresh_expires=refresh_exp,
    )


def test_password_hash_and_verify() -> None:
    hashed = hash_password("my-secret-pass")
    assert hashed != "my-secret-pass"
    assert verify_password("my-secret-pass", hashed) is True
    assert verify_password("wrong-pass", hashed) is False


def test_access_token_claims_and_expiry() -> None:
    auth = _make_auth(access_exp=600, refresh_exp=7200)
    token = auth.create_access_token(UserTokenClaimsEntity(id=42))

    raw = jwt.decode(
        token,
        "test-secret-key-at-least-32-bytes-long",
        algorithms=["HS256"],
        options={"verify_aud": False},
    )
    assert raw["claims"] == {"id": 42}
    assert raw["sub"] == "access-token"
    assert raw["iss"] == "python-django-clean-api"
    assert raw["aud"] == ["user", "admin"]
    assert raw["exp"] - raw["iat"] == 600


def test_refresh_token_uses_refresh_expires_not_access_expires() -> None:
    auth = _make_auth(access_exp=600, refresh_exp=172800)
    token = auth.create_refresh_token(UserTokenClaimsEntity(id=7))

    raw = jwt.decode(
        token,
        "test-secret-key-at-least-32-bytes-long",
        algorithms=["HS256"],
        options={"verify_aud": False},
    )
    assert raw["sub"] == "refresh-token"
    assert raw["exp"] - raw["iat"] == 172800


def test_repeat_refresh_token_retains_original_exp() -> None:
    auth = _make_auth(access_exp=600, refresh_exp=172800)
    original_exp = int(time.time()) + 50000
    token = auth.repeat_refresh_token(UserTokenClaimsEntity(id=9), original_exp)

    parsed = auth.parse_token(token)
    assert parsed.claims.id == 9
    assert parsed.sub == "refresh-token"
    assert parsed.exp == original_exp


def test_parse_token_strips_bearer_prefix() -> None:
    auth = _make_auth()
    token = auth.create_access_token(UserTokenClaimsEntity(id=5))
    parsed = auth.parse_token(f"Bearer {token}")
    assert parsed.claims.id == 5


def test_parse_expired_token_raises_authentication_error() -> None:
    auth = _make_auth(access_exp=-10)
    token = auth.create_access_token(UserTokenClaimsEntity(id=1))
    with pytest.raises(AuthenticationError, match="token had expired"):
        auth.parse_token(token)


def test_parse_invalid_token_raises_authentication_error() -> None:
    auth = _make_auth()
    with pytest.raises(AuthenticationError, match="token format is invalid"):
        auth.parse_token("not-a-valid-jwt")


def test_parse_token_missing_required_claims_raises_authentication_error() -> None:
    auth = _make_auth()
    token = jwt.encode(
        {"claims": {"id": "not-an-int"}},
        "test-secret-key-at-least-32-bytes-long",
        algorithm="HS256",
    )
    with pytest.raises(AuthenticationError, match="token format is invalid"):
        auth.parse_token(token)


def test_parse_token_normalizes_string_audience() -> None:
    auth = _make_auth()
    now = int(time.time())
    token = jwt.encode(
        {"claims": {"id": 1}, "aud": "user", "exp": now + 60, "iat": now},
        "test-secret-key-at-least-32-bytes-long",
        algorithm="HS256",
    )
    parsed = auth.parse_token(token)
    assert parsed.aud == ["user"]
