from __future__ import annotations

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
