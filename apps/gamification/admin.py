from django.contrib import admin

from .models import Badge, UserBadge, UserSeasonScore, UserSkillRating


@admin.register(UserSkillRating)
class UserSkillRatingAdmin(admin.ModelAdmin):
    list_display = ("user", "key", "label", "value")
    list_editable = ("value",)


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    list_display = ("title", "code", "icon", "is_active")


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    list_display = ("user", "badge", "unlocked_at")


@admin.register(UserSeasonScore)
class UserSeasonScoreAdmin(admin.ModelAdmin):
    list_display = ("user", "period", "region", "points")
    list_filter = ("period", "region")
