from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    path("auth/otp/request", views.OTPRequestView.as_view()),
    path("auth/otp/link-status", views.OTPLinkStatusView.as_view()),
    path("auth/otp/verify", views.OTPVerifyView.as_view()),
    path("auth/telegram/webapp", views.TelegramWebAppAuthView.as_view()),
    path("auth/google/callback", views.GoogleAuthStubView.as_view()),
    path("auth/token/refresh", TokenRefreshView.as_view()),
    path("auth/logout", views.LogoutView.as_view()),
    path("accounts/me", views.MeView.as_view()),
    path("accounts/me/organizer-request", views.OrganizerRequestView.as_view()),
    path("accounts/me/avatar", views.AvatarUploadView.as_view()),
    path("accounts/me/friends", views.FriendListView.as_view()),
    path("accounts/me/friends/pending", views.FriendPendingView.as_view()),
    path("accounts/friends/search", views.FriendSearchView.as_view()),
    path("accounts/friends/add", views.FriendAddView.as_view()),
    path("accounts/friends/<int:pk>/accept", views.FriendAcceptView.as_view()),
    path("accounts/friends/<uuid:pk>/profile", views.FriendProfileView.as_view()),
]
