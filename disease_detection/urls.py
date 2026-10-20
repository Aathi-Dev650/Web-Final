from django.urls import path

from .views import (
    test_api,
    create_detection,
    register,
    session_login,
    session_logout,
    session_user,
    update_profile,
    detection_history,
)


urlpatterns = [

    path(
        'test/',
        test_api
    ),

    path(
        'create/',
        create_detection
    ),
    path('auth/register/', register),
    path('auth/login/', session_login),
    path('auth/logout/', session_logout),
    path('auth/me/', session_user),
    path('auth/profile/', update_profile),
    path('history/', detection_history),
]
