from __future__ import annotations

import time
from typing import Any

import jwt

from src.domain.entities.user import ParsedTokenEntity, UserTokenClaimsEntity
from src.domain.exceptions import AuthenticationError

DEFAULT_AUDIENCE: tuple[str, ...] = ("user", "admin")


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
            "exp": exp,
            "nbf": now,
            "iat": now,
        }

    def _encode(self, payload: dict[str, Any]) -> str:
        return jwt.encode(payload, self._secret_key, algorithm="HS256")

    def create_access_token(self, claims: UserTokenClaimsEntity) -> str:
        now = int(time.time())
        payload = self._build_payload(claims, "access-token", now + self._access_expires, now)
        return self._encode(payload)

    def create_refresh_token(self, claims: UserTokenClaimsEntity) -> str:
        now = int(time.time())
        payload = self._build_payload(claims, "refresh-token", now + self._refresh_expires, now)
        return self._encode(payload)

    def repeat_refresh_token(
        self,
        claims: UserTokenClaimsEntity,
        original_exp: int,
    ) -> str:
        now = int(time.time())
        payload = self._build_payload(claims, "refresh-token", original_exp, now)
        return self._encode(payload)

    def parse_token(self, raw_token: str) -> ParsedTokenEntity:
        token = raw_token.removeprefix("Bearer ").strip()
        if not token:
            raise AuthenticationError("token format is invalid")

        try:
            decoded = jwt.decode(
                token,
                self._secret_key,
                algorithms=["HS256"],
                options={"verify_aud": False},
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

        raw_aud = decoded.get("aud", [])
        if isinstance(raw_aud, str):
            audience = [raw_aud]
        elif isinstance(raw_aud, list):
            audience = [str(item) for item in raw_aud]
        else:
            raise AuthenticationError("token format is invalid")

        try:
            user_id = int(claims_dict["id"])
            exp = int(decoded["exp"])
            iat = int(decoded["iat"])
            nbf = int(decoded.get("nbf", iat))
        except (KeyError, TypeError, ValueError) as exc:
            raise AuthenticationError("token format is invalid") from exc

        return ParsedTokenEntity(
            claims=UserTokenClaimsEntity(id=user_id),
            sub=str(decoded.get("sub", "")),
            iss=str(decoded.get("iss", "")),
            aud=audience,
            exp=exp,
            iat=iat,
            nbf=nbf,
        )
