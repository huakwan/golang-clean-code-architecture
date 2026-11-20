from __future__ import annotations

import time

import jwt
import pytest

from src.domain.entities.user import UserTokenClaimsEntity
from src.domain.exceptions import AuthenticationError
from src.shared.authentication.jwt_authentication import (
    ACCESS_TOKEN_SUBJECT,
    REFRESH_TOKEN_SUBJECT,
    JWTAuthenticator,
    hash_token,
    verify_token_hash,
)
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


def test_verify_password_with_missing_hash_executes_dummy_bcrypt_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import bcrypt

    calls: list[tuple[bytes, bytes]] = []
    real_checkpw = bcrypt.checkpw

    def spy_checkpw(password: bytes, hashed: bytes) -> bool:
        calls.append((password, hashed))
        return real_checkpw(password, hashed)

    monkeypatch.setattr(bcrypt, "checkpw", spy_checkpw)
    assert verify_password("some-pass", None) is False
    assert len(calls) == 1


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
    assert isinstance(raw.get("jti"), str) and len(raw["jti"]) > 0


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


def test_parse_token_rejects_bearer_prefix() -> None:
    auth = _make_auth()
    token = auth.create_access_token(UserTokenClaimsEntity(id=5))
    with pytest.raises(AuthenticationError, match="token format is invalid"):
        auth.parse_token(f"Bearer {token}")


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
        {
            "claims": {"id": 1},
            "iss": "python-django-clean-api",
            "sub": ACCESS_TOKEN_SUBJECT,
            "aud": "user",
            "exp": now + 60,
            "iat": now,
        },
        "test-secret-key-at-least-32-bytes-long",
        algorithm="HS256",
    )
    parsed = auth.parse_token(token)
    assert parsed.aud == ["user"]


def test_tokens_include_unique_jti_across_calls() -> None:
    auth = _make_auth()
    claims = UserTokenClaimsEntity(id=10)
    a1 = auth.create_access_token(claims)
    a2 = auth.create_access_token(claims)
    r1 = auth.create_refresh_token(claims)
    r2 = auth.create_refresh_token(claims)
    rep1 = auth.repeat_refresh_token(claims, int(time.time()) + 300)
    rep2 = auth.repeat_refresh_token(claims, int(time.time()) + 300)

    assert a1 != a2
    assert r1 != r2
    assert rep1 != rep2
    assert auth.parse_token(a1).jti != auth.parse_token(a2).jti


def test_parse_token_enforces_expected_sub_iss_aud_and_claims_types() -> None:
    auth = _make_auth()
    access = auth.create_access_token(UserTokenClaimsEntity(id=5))
    refresh = auth.create_refresh_token(UserTokenClaimsEntity(id=5))

    with pytest.raises(AuthenticationError):
        auth.parse_token(refresh, expected_sub=ACCESS_TOKEN_SUBJECT)

    with pytest.raises(AuthenticationError):
        auth.parse_token(access, expected_sub=REFRESH_TOKEN_SUBJECT)

    now = int(time.time())
    secret = "test-secret-key-at-least-32-bytes-long"

    wrong_iss = jwt.encode(
        {
            "claims": {"id": 5},
            "iss": "other-issuer",
            "sub": ACCESS_TOKEN_SUBJECT,
            "aud": ["user"],
            "exp": now + 60,
            "iat": now,
        },
        secret,
        algorithm="HS256",
    )
    with pytest.raises(AuthenticationError):
        auth.parse_token(wrong_iss)

    wrong_aud = jwt.encode(
        {
            "claims": {"id": 5},
            "iss": "python-django-clean-api",
            "sub": ACCESS_TOKEN_SUBJECT,
            "aud": ["external"],
            "exp": now + 60,
            "iat": now,
        },
        secret,
        algorithm="HS256",
    )
    with pytest.raises(AuthenticationError):
        auth.parse_token(wrong_aud)

    missing_sub = jwt.encode(
        {
            "claims": {"id": 5},
            "iss": "python-django-clean-api",
            "aud": ["user"],
            "exp": now + 60,
            "iat": now,
        },
        secret,
        algorithm="HS256",
    )
    with pytest.raises(AuthenticationError):
        auth.parse_token(missing_sub)

    bool_id = jwt.encode(
        {
            "claims": {"id": True},
            "iss": "python-django-clean-api",
            "sub": ACCESS_TOKEN_SUBJECT,
            "aud": ["user"],
            "exp": now + 60,
            "iat": now,
        },
        secret,
        algorithm="HS256",
    )
    with pytest.raises(AuthenticationError):
        auth.parse_token(bool_id)


def test_hash_token_and_verify_token_hash() -> None:
    raw = "header.payload.signature"
    digest = hash_token(raw)
    assert digest != raw
    assert len(digest) == 64
    assert verify_token_hash(raw, digest) is True
    assert verify_token_hash("different.token.value", digest) is False
