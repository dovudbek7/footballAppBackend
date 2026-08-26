from django.contrib import admin

from .models import DeviceToken, NotificationLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("user", "type", "status", "created_at")
    list_filter = ("type", "status")
    readonly_fields = [f.name for f in NotificationLog._meta.fields]


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "platform", "device_id", "is_active", "created_at")
    list_filter = ("platform", "is_active")
    search_fields = ("token", "device_id", "user__full_name")
