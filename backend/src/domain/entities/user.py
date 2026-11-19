from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

EMAIL_REGEX = re.compile(r"^[\w\-.]+@([\w-]+\.)+[\w-]{2,4}$")


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

    def is_valid_email(self) -> bool:
        return bool(self.email and EMAIL_REGEX.match(self.email))


@dataclass(frozen=True)
class UserLoginRequest:
    email: str
    password: str


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
