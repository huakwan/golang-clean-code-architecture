from __future__ import annotations

from django.urls import include, path

from src.interfaces.handlers.django.modules.monitor import MonitorHealthCheckView

urlpatterns = [
    path("", MonitorHealthCheckView.as_view(), name="monitor-health"),
    path("users/", include("src.infrastructure.django_app.urls.user_urls")),
    path("data/", include("src.infrastructure.django_app.urls.crud_urls")),
]
