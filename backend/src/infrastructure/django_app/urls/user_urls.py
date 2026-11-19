from __future__ import annotations

from django.urls import re_path

from src.interfaces.handlers.django.modules.user import (
    UserLoginView,
    UserLogoutView,
    UserProfileView,
    UserRefreshTokenView,
    UserRegisterView,
)

urlpatterns = [
    re_path(r"^register/?$", UserRegisterView.as_view(), name="user-register"),
    re_path(r"^login/?$", UserLoginView.as_view(), name="user-login"),
    re_path(r"^refresh-token/?$", UserRefreshTokenView.as_view(), name="user-refresh-token"),
    re_path(r"^logout/?$", UserLogoutView.as_view(), name="user-logout"),
    re_path(r"^profile/?$", UserProfileView.as_view(), name="user-profile"),
]
