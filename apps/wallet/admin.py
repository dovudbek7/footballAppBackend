from django.contrib import admin
from django.utils import timezone

from apps.notifications.models import NotificationLog
from apps.notifications.services import notify

from . import services
from .models import ExchangeRate, PaymentMethod, TopUpRequest, Transaction, Wallet


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "balance_usd", "paynet_id")
    search_fields = ("user__phone", "user__full_name", "paynet_id")


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ("currency_pair", "rate", "created_at", "updated_by")

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ("name", "key", "icon", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order")


@admin.action(description="Approve selected top-up requests (credits wallet)")
def approve_topups(modeladmin, request, queryset):
    for topup in queryset.filter(status=TopUpRequest.Status.PENDING):
        services.credit(
            topup.user,
            topup.amount,
            title="Wallet top-up",
            subtitle=topup.payment_method.name,
            topup_request=topup,
        )
        topup.status = TopUpRequest.Status.APPROVED
        topup.reviewed_by = request.user
        topup.reviewed_at = timezone.now()
        topup.save(update_fields=["status", "reviewed_by", "reviewed_at"])
        notify(topup.user, NotificationLog.NotificationType.TOPUP_APPROVED, amount=topup.amount)


@admin.action(description="Reject selected top-up requests")
def reject_topups(modeladmin, request, queryset):
    queryset.filter(status=TopUpRequest.Status.PENDING).update(
        status=TopUpRequest.Status.REJECTED, reviewed_by=request.user, reviewed_at=timezone.now()
    )


@admin.register(TopUpRequest)
class TopUpRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "payment_method", "status", "created_at")
    list_filter = ("status", "payment_method")
    actions = [approve_topups, reject_topups]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("wallet", "kind", "amount", "status", "title", "created_at")
    list_filter = ("kind", "status")
