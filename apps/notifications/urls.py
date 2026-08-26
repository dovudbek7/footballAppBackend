from django.urls import path

from . import views

urlpatterns = [
    path("notifications", views.NotificationListView.as_view()),
    path("notifications/unread-count", views.NotificationUnreadCountView.as_view()),
    path("notifications/read-all", views.NotificationMarkAllReadView.as_view()),
    path("notifications/<int:pk>/read", views.NotificationMarkReadView.as_view()),
    path("notifications/devices/", views.DeviceTokenRegisterView.as_view()),
    path("notifications/devices/unregister/", views.DeviceTokenUnregisterView.as_view()),
]
