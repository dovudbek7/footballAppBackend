from django.urls import path

from . import views

urlpatterns = [
    path("wallet", views.WalletView.as_view()),
    path("wallet/transactions", views.TransactionListView.as_view()),
    path("wallet/payment-methods", views.PaymentMethodListView.as_view()),
    path("wallet/topup-requests", views.TopUpRequestListCreateView.as_view()),
]
