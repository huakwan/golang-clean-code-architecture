from __future__ import annotations

from django.urls import re_path

from src.infrastructure.container import get_container
from src.interfaces.handlers.django.modules.crud import (
    CrudDescribeView,
    CrudDetailView,
    CrudListCreateView,
    CrudModelListView,
)
from src.usecases.crud.crud_usecase import CrudUsecase


def _get_crud_usecase() -> CrudUsecase:
    return get_container().crud_usecase


urlpatterns = [
    re_path(
        r"^models/?$",
        CrudModelListView.as_view(usecase_provider=_get_crud_usecase),
        name="crud-models",
    ),
    re_path(
        r"^(?P<entity_model_slug>[a-z0-9-]+)/describe/?$",
        CrudDescribeView.as_view(usecase_provider=_get_crud_usecase),
        name="crud-describe",
    ),
    re_path(
        r"^(?P<entity_model_slug>[a-z0-9-]+)/?$",
        CrudListCreateView.as_view(usecase_provider=_get_crud_usecase),
        name="crud-list-create",
    ),
    re_path(
        r"^(?P<entity_model_slug>[a-z0-9-]+)/(?P<record_id>[^/]+)/?$",
        CrudDetailView.as_view(usecase_provider=_get_crud_usecase),
        name="crud-detail",
    ),
]
