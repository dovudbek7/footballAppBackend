from django.urls import path

from . import views

urlpatterns = [
    path("profile/stats", views.ProfileStatsView.as_view()),
    path("profile/badges", views.ProfileBadgesView.as_view()),
    path("profile/activity", views.ProfileActivityView.as_view()),
    path("leaderboard", views.LeaderboardView.as_view()),
]
