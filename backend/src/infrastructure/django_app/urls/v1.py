from __future__ import annotations

from django.urls import include, path

from src.domain.entities.monitor import MonitorEntity
from src.infrastructure.container import get_container
from src.interfaces.handlers.django.modules.monitor import MonitorHealthCheckView


def _get_monitor_entity() -> MonitorEntity:
    cfg = get_container().config
    return MonitorEntity(name=cfg.name, version=cfg.version)


urlpatterns = [
    path(
        "",
        MonitorHealthCheckView.as_view(monitor_provider=_get_monitor_entity),
        name="monitor-health",
    ),
    path("users/", include("src.infrastructure.django_app.urls.user_urls")),
    path("data/", include("src.infrastructure.django_app.urls.crud_urls")),
]
