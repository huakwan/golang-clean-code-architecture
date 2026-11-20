from __future__ import annotations

from pathlib import Path

from src.config.env_config import get_config

BASE_DIR = Path(__file__).resolve().parents[2]
_cfg = get_config()

SECRET_KEY = _cfg.secret_key
DEBUG = _cfg.debug
ALLOWED_HOSTS = ["*"]
APPEND_SLASH = False

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "src.infrastructure.database.postgres.apps.PostgresDatabaseConfig",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "src.infrastructure.django_app.middlewares.RequestLoggerMiddleware",
    "src.infrastructure.django_app.middlewares.JSON404Middleware",
]

ROOT_URLCONF = "src.config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

WSGI_APPLICATION = "src.config.wsgi.application"
ASGI_APPLICATION = "src.config.asgi.application"

if _cfg.use_sqlite:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": _cfg.postgres_db_name,
            "USER": _cfg.postgres_db_user,
            "PASSWORD": _cfg.postgres_db_password,
            "HOST": _cfg.postgres_db_host,
            "PORT": _cfg.postgres_db_port,
        }
    }

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = False
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

CORS_ALLOWED_ORIGINS = list(_cfg.cors_allowed_origins)
CORS_ALLOW_CREDENTIALS = True
TRUSTED_PROXIES = _cfg.trusted_proxies

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "src.infrastructure.django_app.authentication.CustomJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_THROTTLE_CLASSES": [
        "src.infrastructure.django_app.throttling.ClientIPScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "auth_register": _cfg.throttle_auth_register,
        "auth_login": _cfg.throttle_auth_login,
        "auth_refresh": _cfg.throttle_auth_refresh,
        "auth_logout": _cfg.throttle_auth_logout,
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": (
        "src.interfaces.handlers.django.entities.response.custom_exception_handler"
    ),
    "UNAUTHENTICATED_USER": None,
}

SPECTACULAR_SETTINGS = {
    "TITLE": _cfg.name,
    "DESCRIPTION": (
        "Python Django + DRF re-implementation of Clean Code Architecture "
        "with JWT Auth, Polyglot Dynamic CRUD (PostgreSQL & MongoDB), and Avro Schemas."
    ),
    "VERSION": _cfg.version,
    "SERVE_INCLUDE_SCHEMA": False,
    "SECURITY": [{"BearerAuth": []}],
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "loggers": {
        "api.request": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "src": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
