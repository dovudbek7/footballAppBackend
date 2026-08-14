from django.urls import path

from . import views

urlpatterns = [
    path("matches/mine", views.MyMatchesView.as_view()),
    path("matches/next", views.NextMatchView.as_view()),
    path("matches/<uuid:pk>", views.MatchDetailView.as_view()),
    path("matches/<uuid:pk>/join", views.JoinMatchView.as_view()),
    path("matches/<uuid:pk>/result", views.MatchResultView.as_view()),
    path("matches/<uuid:pk>/chat", views.MatchChatView.as_view()),
    path("bookings/<uuid:pk>/accept-split", views.AcceptSplitView.as_view()),
    path("bookings/<uuid:pk>/cancel", views.CancelBookingView.as_view()),
]
