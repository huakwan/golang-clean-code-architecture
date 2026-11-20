from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

_LOCAL_PART_REGEX = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+$")
_DOMAIN_LABEL_REGEX = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")
_TLD_REGEX = re.compile(r"^[A-Za-z]{2,63}$")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def is_valid_email_address(email: str) -> bool:
    if not email or len(email) > 254:
        return False
    local, sep, domain = email.partition("@")
    if not sep or "@" in domain or not local or not domain or len(local) > 64:
        return False
    if local.startswith(".") or local.endswith(".") or ".." in local:
        return False
    if not _LOCAL_PART_REGEX.match(local):
        return False
    labels = domain.split(".")
    if len(labels) < 2:
        return False
    if not all(_DOMAIN_LABEL_REGEX.match(label) for label in labels):
        return False
    return bool(_TLD_REGEX.match(labels[-1]))


@dataclass(frozen=True)
class UserEntity:
    id: int
    email: str
    first_name: str
    last_name: str
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UserTokenEntity:
    access: str
    refresh: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UserTokenClaimsEntity:
    id: int


@dataclass(frozen=True)
class ParsedTokenEntity:
    claims: UserTokenClaimsEntity
    sub: str
    iss: str
    aud: list[str]
    exp: int
    iat: int
    nbf: int
    jti: str = ""


@dataclass(frozen=True)
class UserPermissionEntity:
    id: int
    user_id: int
    permission: str
    updated_at: str = ""


@dataclass(frozen=True)
class UserRegisterRequest:
    email: str
    password: str
    first_name: str
    last_name: str

    def normalized_email(self) -> str:
        return normalize_email(self.email)

    def is_valid_email(self) -> bool:
        return is_valid_email_address(self.normalized_email())


@dataclass(frozen=True)
class UserLoginRequest:
    email: str
    password: str

    def normalized_email(self) -> str:
        return normalize_email(self.email)


@dataclass(frozen=True)
class UserLoginResponse:
    user: UserEntity
    token: UserTokenEntity

    def to_dict(self) -> dict[str, Any]:
        return {
            "user": self.user.to_dict(),
            "token": self.token.to_dict(),
        }


@dataclass(frozen=True)
class UserRefreshTokenRequest:
    refresh_token: str


@dataclass(frozen=True)
class UserLogoutRequest:
    refresh_token: str
