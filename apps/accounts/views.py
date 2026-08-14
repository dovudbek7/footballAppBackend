from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from . import services
from .models import Friendship, User
from .serializers import (
    FriendAddSerializer,
    FriendSerializer,
    OTPRequestSerializer,
    OTPVerifySerializer,
    TelegramWebAppAuthSerializer,
    UserOnboardSerializer,
    UserSerializer,
)


def _tokens_for(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class OTPRequestView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = services.request_otp(serializer.validated_data["phone"])
        return Response(result)


class OTPLinkStatusView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get("token")
        if not token:
            return Response({"detail": "token is required"}, status=status.HTTP_400_BAD_REQUEST)
        return Response(services.link_status(token))


class OTPVerifyView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user, created = services.verify_otp(**serializer.validated_data)
        except services.TelegramAuthError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {**_tokens_for(user), "user": UserSerializer(user).data, "is_new_user": created}
        )


class TelegramWebAppAuthView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = TelegramWebAppAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            user, created = services.authenticate_telegram_webapp(serializer.validated_data["init_data"])
        except services.TelegramAuthError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {**_tokens_for(user), "user": UserSerializer(user).data, "is_new_user": created}
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response({"detail": "refresh is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            RefreshToken(refresh).blacklist()
        except Exception:
            return Response({"detail": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)
        return Response(status=status.HTTP_205_RESET_CONTENT)


class GoogleAuthStubView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        return Response(
            {"detail": "Google login is not implemented yet."},
            status=status.HTTP_501_NOT_IMPLEMENTED,
        )


class MeView(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return UserOnboardSerializer
        return UserSerializer


class FriendListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FriendSerializer

    def get_queryset(self):
        ids = Friendship.objects.filter(
            user=self.request.user, status=Friendship.Status.ACCEPTED
        ).values_list("friend_id", flat=True)
        return User.objects.filter(id__in=ids)


class FriendAddView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = FriendAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        friend = None
        if data.get("phone"):
            friend = User.objects.filter(phone=data["phone"]).first()
        if not friend and data.get("telegram_username"):
            friend = User.objects.filter(telegram_username=data["telegram_username"].lstrip("@")).first()
        if not friend:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        if friend.id == request.user.id:
            return Response({"detail": "Cannot friend yourself."}, status=status.HTTP_400_BAD_REQUEST)
        friendship, _ = Friendship.objects.get_or_create(user=request.user, friend=friend)
        return Response({"id": friendship.id, "status": friendship.status}, status=status.HTTP_201_CREATED)


class FriendAcceptView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        friendship = Friendship.objects.filter(
            id=pk, friend=request.user, status=Friendship.Status.PENDING
        ).first()
        if not friendship:
            return Response({"detail": "Friend request not found."}, status=status.HTTP_404_NOT_FOUND)
        friendship.status = Friendship.Status.ACCEPTED
        friendship.save(update_fields=["status"])
        Friendship.objects.get_or_create(
            user=request.user, friend=friendship.user, defaults={"status": Friendship.Status.ACCEPTED}
        )
        return Response({"status": "accepted"})
