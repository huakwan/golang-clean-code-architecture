from __future__ import annotations

import hashlib
import hmac
import time
import uuid
from typing import Any

import jwt

from src.domain.entities.user import ParsedTokenEntity, UserTokenClaimsEntity
from src.domain.exceptions import AuthenticationError

DEFAULT_AUDIENCE: tuple[str, ...] = ("user", "admin")
ACCESS_TOKEN_SUBJECT = "access-token"  # noqa: S105
REFRESH_TOKEN_SUBJECT = "refresh-token"  # noqa: S105


def hash_token(raw_token: str) -> str:
    """Return the hex SHA-256 digest of a raw JWT for secure persistence."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def verify_token_hash(raw_token: str, stored_hash: str) -> bool:
    """Compare a raw JWT against its stored SHA-256 digest in constant time."""
    return hmac.compare_digest(hash_token(raw_token), stored_hash)


class JWTAuthenticator:
    """HS256 JWT signer & parser matching the Go reference claims contract."""

    def __init__(
        self,
        *,
        secret_key: str,
        app_name: str,
        access_expires: int,
        refresh_expires: int,
    ) -> None:
        self._secret_key = secret_key
        self._issuer = app_name.strip().lower().replace(" ", "-")
        self._access_expires = access_expires
        self._refresh_expires = refresh_expires

    def _build_payload(
        self,
        claims: UserTokenClaimsEntity,
        subject: str,
        exp: int,
        now: int,
    ) -> dict[str, Any]:
        return {
            "claims": {"id": claims.id},
            "iss": self._issuer,
            "sub": subject,
            "aud": list(DEFAULT_AUDIENCE),
            "jti": uuid.uuid4().hex,
            "exp": exp,
            "nbf": now,
            "iat": now,
        }

    def _encode(self, payload: dict[str, Any]) -> str:
        return jwt.encode(payload, self._secret_key, algorithm="HS256")

    def create_access_token(self, claims: UserTokenClaimsEntity) -> str:
        now = int(time.time())
        payload = self._build_payload(claims, ACCESS_TOKEN_SUBJECT, now + self._access_expires, now)
        return self._encode(payload)

    def create_refresh_token(self, claims: UserTokenClaimsEntity) -> str:
        now = int(time.time())
        payload = self._build_payload(
            claims,
            REFRESH_TOKEN_SUBJECT,
            now + self._refresh_expires,
            now,
        )
        return self._encode(payload)

    def repeat_refresh_token(
        self,
        claims: UserTokenClaimsEntity,
        original_exp: int,
    ) -> str:
        now = int(time.time())
        payload = self._build_payload(claims, REFRESH_TOKEN_SUBJECT, original_exp, now)
        return self._encode(payload)

    def parse_token(
        self,
        raw_token: str,
        *,
        expected_sub: str | None = None,
    ) -> ParsedTokenEntity:
        token = raw_token.strip()
        if not token:
            raise AuthenticationError("token format is invalid")

        try:
            decoded = jwt.decode(
                token,
                self._secret_key,
                algorithms=["HS256"],
                issuer=self._issuer,
                audience=list(DEFAULT_AUDIENCE),
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationError("token had expired") from exc
        except jwt.InvalidAlgorithmError as exc:
            raise AuthenticationError("signing method is invalid") from exc
        except jwt.PyJWTError as exc:
            raise AuthenticationError("token format is invalid") from exc

        claims_dict = decoded.get("claims")
        if not isinstance(claims_dict, dict) or "id" not in claims_dict:
            raise AuthenticationError("token format is invalid")

        raw_id = claims_dict["id"]
        if isinstance(raw_id, bool):
            raise AuthenticationError("token format is invalid")

        raw_aud = decoded.get("aud", [])
        if isinstance(raw_aud, str):
            audience = [raw_aud]
        elif isinstance(raw_aud, list):
            audience = [str(item) for item in raw_aud]
        else:
            raise AuthenticationError("token format is invalid")

        sub = str(decoded.get("sub", ""))
        if expected_sub is not None and sub != expected_sub:
            raise AuthenticationError("token type is invalid")

        try:
            user_id = int(raw_id)
            exp = int(decoded["exp"])
            iat = int(decoded["iat"])
            nbf = int(decoded.get("nbf", iat))
        except (KeyError, TypeError, ValueError) as exc:
            raise AuthenticationError("token format is invalid") from exc

        return ParsedTokenEntity(
            claims=UserTokenClaimsEntity(id=user_id),
            sub=sub,
            iss=str(decoded.get("iss", "")),
            aud=audience,
            exp=exp,
            iat=iat,
            nbf=nbf,
            jti=str(decoded.get("jti", "")),
        )
