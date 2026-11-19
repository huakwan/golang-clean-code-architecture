from __future__ import annotations

from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("api/v1/", include("src.infrastructure.django_app.urls.v1")),
    path("api/schema/", SpectacularAPIView.as_view(), name="openapi-schema"),
    path("swagger/", SpectacularSwaggerView.as_view(url_name="openapi-schema"), name="swagger-ui"),
]
