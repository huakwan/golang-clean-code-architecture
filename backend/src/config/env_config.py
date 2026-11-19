from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

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


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@lru_cache(maxsize=1)
def get_config() -> AppConfig:
    env_path = BASE_DIR / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    raw_origins = os.getenv(
        "APP_CORS_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    origins = tuple(o.strip() for o in raw_origins.split(",") if o.strip())

    return AppConfig(
        host=os.getenv("APP_HOST", "127.0.0.1"),
        port=int(os.getenv("APP_PORT", "8000")),
        name=os.getenv("APP_NAME", "PYTHON DJANGO CLEAN API"),
        version=os.getenv("APP_VERSION", "0.0.1"),
        debug=_parse_bool(os.getenv("APP_DEBUG"), default=True),
        postgres_db_name=os.getenv("APP_POSTGRES_DB_NAME", "postgres"),
        postgres_db_user=os.getenv("APP_POSTGRES_DB_USER", "postgres"),
        postgres_db_password=os.getenv("APP_POSTGRES_DB_PASSWORD", "golang-first-api"),
        postgres_db_host=os.getenv("APP_POSTGRES_DB_HOST", "localhost"),
        postgres_db_port=int(os.getenv("APP_POSTGRES_DB_PORT", "5432")),
        mongodb_uri=os.getenv(
            "APP_MONGODB_DB_ATLAS_URI",
            "mongodb://root:golang-first-api@127.0.0.1:27017/?authMechanism=SCRAM-SHA-1&authSource=admin",
        ),
        mongodb_db_name=os.getenv("APP_MONGODB_DB_NAME", "django_cleancode_example"),
        secret_key=os.getenv("APP_SECRET_KEY", "1234567890-change-me-in-production"),
        jwt_access_expires=int(os.getenv("APP_JWT_ACCESS_EXPIRES", "86400")),
        jwt_refresh_expires=int(os.getenv("APP_JWT_REFRESH_EXPIRES", "172800")),
        cors_allowed_origins=origins,
    )
