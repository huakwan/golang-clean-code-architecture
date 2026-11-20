from __future__ import annotations

import os
from pathlib import Path

from src.config import env_config


def test_default_postgres_db_name_is_postgres(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("APP_POSTGRES_DB_NAME", raising=False)
    monkeypatch.setattr(env_config, "BASE_DIR", tmp_path)
    env_config.get_config.cache_clear()

    try:
        cfg = env_config.get_config()
        assert cfg.postgres_db_name == "postgres"
    finally:
        env_config.get_config.cache_clear()


def test_security_and_throttle_defaults_and_trusted_proxies_parsing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("APP_TRUSTED_PROXIES", raising=False)
    monkeypatch.delenv("APP_THROTTLE_AUTH_REGISTER", raising=False)
    monkeypatch.delenv("APP_THROTTLE_AUTH_LOGIN", raising=False)
    monkeypatch.delenv("APP_THROTTLE_AUTH_REFRESH", raising=False)
    monkeypatch.delenv("APP_THROTTLE_AUTH_LOGOUT", raising=False)
    monkeypatch.setattr(env_config, "BASE_DIR", tmp_path)
    env_config.get_config.cache_clear()

    try:
        cfg = env_config.get_config()
        assert cfg.trusted_proxies == ()
        assert cfg.throttle_auth_register == "10/min"
        assert cfg.throttle_auth_login == "10/min"
        assert cfg.throttle_auth_refresh == "20/min"
        assert cfg.throttle_auth_logout == "20/min"

        monkeypatch.setenv("APP_TRUSTED_PROXIES", "127.0.0.1, 10.0.0.0/8, ")
        env_config.get_config.cache_clear()
        parsed_cfg = env_config.get_config()
        assert parsed_cfg.trusted_proxies == ("127.0.0.1", "10.0.0.0/8")
    finally:
        env_config.get_config.cache_clear()


def test_get_config_reads_dotenv_without_mutating_os_environ_and_tracks_use_sqlite(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("APP_NAME", raising=False)
    monkeypatch.delenv("APP_PORT", raising=False)
    monkeypatch.delenv("DJANGO_USE_SQLITE", raising=False)
    (tmp_path / ".env").write_text(
        "APP_NAME=DOTENV APP\nAPP_PORT=9123\nDJANGO_USE_SQLITE=true\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(env_config, "BASE_DIR", tmp_path)
    env_config.get_config.cache_clear()

    try:
        cfg = env_config.get_config()
        assert cfg.name == "DOTENV APP"
        assert cfg.port == 9123
        assert cfg.use_sqlite is True
        assert "APP_NAME" not in os.environ
        assert "APP_PORT" not in os.environ

        monkeypatch.setenv("APP_NAME", "ENV OVERRIDE")
        env_config.get_config.cache_clear()
        overridden = env_config.get_config()
        assert overridden.name == "ENV OVERRIDE"
        assert overridden.port == 9123
    finally:
        env_config.get_config.cache_clear()
