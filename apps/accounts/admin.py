from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Friendship, OTPCode, TelegramLinkToken, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User
    list_display = ("id", "phone", "telegram_id", "full_name", "experience_level", "is_onboarded", "is_staff")
    search_fields = ("phone", "telegram_id", "full_name", "telegram_username")
    ordering = ("-created_at",)
    fieldsets = (
        (None, {"fields": ("phone", "telegram_id", "telegram_username", "password")}),
        ("Profile", {"fields": ("full_name", "avatar_url", "region", "city", "position", "experience_level")}),
        ("Status", {"fields": ("is_onboarded", "is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("phone", "telegram_id", "password1", "password2")}),
    )
    filter_horizontal = ("groups", "user_permissions")


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ("phone", "code", "purpose", "expires_at", "consumed_at", "attempts")
    search_fields = ("phone",)


@admin.register(TelegramLinkToken)
class TelegramLinkTokenAdmin(admin.ModelAdmin):
    list_display = ("phone", "token", "status", "telegram_id", "expires_at")
    search_fields = ("phone", "token")


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ("user", "friend", "status", "created_at")
