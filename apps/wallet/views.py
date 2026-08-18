from django.utils import timezone
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import PaymentMethod, TopUpRequest, Transaction
from .serializers import (
    PaymentMethodSerializer,
    TopUpRequestSerializer,
    TransactionSerializer,
    WalletSerializer,
)
from .services import credit, get_or_create_wallet


class WalletView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        wallet = get_or_create_wallet(request.user)
        return Response(WalletSerializer(wallet).data)


class TransactionListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionSerializer

    def get_queryset(self):
        wallet = get_or_create_wallet(self.request.user)
        return wallet.transactions.all()


class PaymentMethodListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentMethodSerializer
    queryset = PaymentMethod.objects.filter(is_active=True)
    pagination_class = None


class TopUpRequestListCreateView(generics.ListCreateAPIView):
    """Real payment gateways aren't wired up yet, so top-ups are credited
    instantly on submission instead of waiting on admin review."""

    permission_classes = [IsAuthenticated]
    serializer_class = TopUpRequestSerializer

    def get_queryset(self):
        return TopUpRequest.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        topup = serializer.save(
            user=self.request.user,
            status=TopUpRequest.Status.APPROVED,
            reviewed_at=timezone.now(),
        )
        credit(
            self.request.user,
            topup.amount,
            title="Top-up",
            subtitle=topup.payment_method.name,
            topup_request=topup,
        )
