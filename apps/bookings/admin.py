from django.contrib import admin

from .models import Booking, Match, MatchResult


class BookingInline(admin.TabularInline):
    model = Booking
    extra = 0
    fields = ("user", "invited_by", "payment_status", "amount_charged", "personal_result", "is_motm")


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("stadium", "date", "start_time", "status", "capacity", "price_per_seat")
    list_filter = ("status", "stadium")
    inlines = [BookingInline]


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("match", "user", "payment_status", "amount_charged", "personal_result", "is_motm")
    list_filter = ("payment_status",)


@admin.register(MatchResult)
class MatchResultAdmin(admin.ModelAdmin):
    list_display = ("match", "score", "entered_by", "created_at")
