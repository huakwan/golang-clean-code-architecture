from __future__ import annotations

import os

from src.config.settings import *  # noqa: F401, F403

if os.getenv("USE_POSTGRES_TESTS", "").lower() not in {"1", "true", "yes"}:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
