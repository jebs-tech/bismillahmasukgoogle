from django.urls import path
from .api_views import (
    RegisterAPI,
    LoginAPI,
    LogoutAPI,
    GetProfileAPI,
    UpdateProfileAPI,
    PreferredTeamsAPI,
    UpdatePreferredTeamsAPI
)

urlpatterns = [
    path("register/", RegisterAPI.as_view()),
    path("login/", LoginAPI.as_view()),
    path("logout/", LogoutAPI.as_view()),

    path("profile/", GetProfileAPI.as_view()),
    path("profile/update/", UpdateProfileAPI.as_view()),

    path("preferred-teams/", PreferredTeamsAPI.as_view()),
    path("preferred-teams/update/", UpdatePreferredTeamsAPI.as_view()),
]
