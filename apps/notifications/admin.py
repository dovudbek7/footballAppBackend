from django.contrib import admin

from .models import NotificationLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("user", "type", "status", "created_at")
    list_filter = ("type", "status")
    readonly_fields = [f.name for f in NotificationLog._meta.fields]
