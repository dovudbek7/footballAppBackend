from django.urls import path

from . import views

urlpatterns = [
    path("stadiums", views.StadiumListView.as_view()),
    path("stadiums/<uuid:pk>", views.StadiumDetailView.as_view()),
    path("stadiums/<uuid:pk>/slots", views.StadiumSlotsView.as_view()),
    path("stadiums/<uuid:pk>/favorite", views.FavoriteToggleView.as_view()),
    path("stadiums/<uuid:pk>/reviews", views.ReviewListCreateView.as_view()),
]
