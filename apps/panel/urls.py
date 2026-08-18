from django.urls import path

from . import views

app_name = "panel"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("", views.dashboard, name="dashboard"),
    path("users/", views.users_list, name="users"),
    path("users/<uuid:pk>/", views.user_detail, name="user_detail"),
    path("organizer-requests/", views.organizer_requests, name="organizer_requests"),
    path("admins/", views.admins_list, name="admins"),
]
