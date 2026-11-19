from __future__ import annotations

from django.apps import AppConfig


class PostgresDatabaseConfig(AppConfig):
    default_auto_field = "django.db.models.AutoField"
    name = "src.infrastructure.database.postgres"
    label = "postgres_db"
