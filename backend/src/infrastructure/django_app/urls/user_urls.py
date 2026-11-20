from __future__ import annotations

from django.urls import re_path

from src.infrastructure.container import get_container
from src.interfaces.handlers.django.modules.user import (
    UserLoginView,
    UserLogoutView,
    UserProfileView,
    UserRefreshTokenView,
    UserRegisterView,
)
from src.usecases.user.user_usecase import UserUsecase


def _get_user_usecase() -> UserUsecase:
    return get_container().user_usecase


urlpatterns = [
    re_path(
        r"^register/?$",
        UserRegisterView.as_view(usecase_provider=_get_user_usecase),
        name="user-register",
    ),
    re_path(
        r"^login/?$",
        UserLoginView.as_view(usecase_provider=_get_user_usecase),
        name="user-login",
    ),
    re_path(
        r"^refresh-token/?$",
        UserRefreshTokenView.as_view(usecase_provider=_get_user_usecase),
        name="user-refresh-token",
    ),
    re_path(
        r"^logout/?$",
        UserLogoutView.as_view(usecase_provider=_get_user_usecase),
        name="user-logout",
    ),
    re_path(
        r"^profile/?$",
        UserProfileView.as_view(usecase_provider=_get_user_usecase),
        name="user-profile",
    ),
]
