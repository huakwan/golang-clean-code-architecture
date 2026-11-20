from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import dotenv_values

BASE_DIR = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class AppConfig:
    host: str
    port: int
    name: str
    version: str
    debug: bool
    postgres_db_name: str
    postgres_db_user: str
    postgres_db_password: str
    postgres_db_host: str
    postgres_db_port: int
    mongodb_uri: str
    mongodb_db_name: str
    secret_key: str
    jwt_access_expires: int
    jwt_refresh_expires: int
    cors_allowed_origins: tuple[str, ...]
    trusted_proxies: tuple[str, ...] = ()
    throttle_auth_register: str = "10/min"
    throttle_auth_login: str = "10/min"
    throttle_auth_refresh: str = "20/min"
    throttle_auth_logout: str = "20/min"
    use_sqlite: bool = False


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _parse_csv(raw: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in raw.split(",") if item.strip())


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    env_path = BASE_DIR / ".env"
    file_env = dotenv_values(env_path) if env_path.exists() else {}

    def _env(key: str, default: str) -> str:
        if key in os.environ:
            return os.environ[key]
        val = file_env.get(key)
        return val if val is not None else default

    def _env_optional(key: str) -> str | None:
        if key in os.environ:
            return os.environ[key]
        return file_env.get(key)

    raw_origins = _env(
        "APP_CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    origins = _parse_csv(raw_origins)
    trusted_proxies = _parse_csv(_env("APP_TRUSTED_PROXIES", ""))

    return AppConfig(
        host=_env("APP_HOST", "127.0.0.1"),
        port=int(_env("APP_PORT", "8000")),
        name=_env("APP_NAME", "PYTHON DJANGO CLEAN API"),
        version=_env("APP_VERSION", "0.0.1"),
        debug=_parse_bool(_env_optional("APP_DEBUG"), default=True),
        postgres_db_name=_env("APP_POSTGRES_DB_NAME", "postgres"),
        postgres_db_user=_env("APP_POSTGRES_DB_USER", "postgres"),
        postgres_db_password=_env("APP_POSTGRES_DB_PASSWORD", "golang-first-api"),
        postgres_db_host=_env("APP_POSTGRES_DB_HOST", "localhost"),
        postgres_db_port=int(_env("APP_POSTGRES_DB_PORT", "5432")),
        mongodb_uri=_env(
            "APP_MONGODB_DB_ATLAS_URI",
            "mongodb://root:golang-first-api@127.0.0.1:27017/?authMechanism=SCRAM-SHA-1&authSource=admin",
        ),
        mongodb_db_name=_env("APP_MONGODB_DB_NAME", "django_cleancode_example"),
        secret_key=_env("APP_SECRET_KEY", "1234567890-change-me-in-production"),
        jwt_access_expires=int(_env("APP_JWT_ACCESS_EXPIRES", "86400")),
        jwt_refresh_expires=int(_env("APP_JWT_REFRESH_EXPIRES", "172800")),
        cors_allowed_origins=origins,
        trusted_proxies=trusted_proxies,
        throttle_auth_register=_env("APP_THROTTLE_AUTH_REGISTER", "10/min"),
        throttle_auth_login=_env("APP_THROTTLE_AUTH_LOGIN", "10/min"),
        throttle_auth_refresh=_env("APP_THROTTLE_AUTH_REFRESH", "20/min"),
        throttle_auth_logout=_env("APP_THROTTLE_AUTH_LOGOUT", "20/min"),
        use_sqlite=_parse_bool(_env_optional("DJANGO_USE_SQLITE"), default=False),
    )
