from __future__ import annotations

from django.urls import re_path

from src.interfaces.handlers.django.modules.crud import (
    CrudDescribeView,
    CrudDetailView,
    CrudListCreateView,
    CrudModelListView,
)

urlpatterns = [
    re_path(r"^models/?$", CrudModelListView.as_view(), name="crud-models"),
    re_path(
        r"^(?P<entity_model_slug>[a-z0-9-]+)/describe/?$",
        CrudDescribeView.as_view(),
        name="crud-describe",
    ),
    re_path(
        r"^(?P<entity_model_slug>[a-z0-9-]+)/?$",
        CrudListCreateView.as_view(),
        name="crud-list-create",
    ),
    re_path(
        r"^(?P<entity_model_slug>[a-z0-9-]+)/(?P<record_id>[^/]+)/?$",
        CrudDetailView.as_view(),
        name="crud-detail",
    ),
]
