import uuid as uuid_lib

from django.core.files.storage import default_storage
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.notifications.models import NotificationLog
from apps.notifications.services import notify
from apps.wallet.models import Wallet

from . import services
from .models import Friendship, User
from .serializers import (
    FriendAddSerializer,
    FriendRequestSerializer,
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


class AvatarUploadView(APIView):
    permission_classes = [IsAuthenticated]

    CONTENT_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
    MAX_SIZE = 5 * 1024 * 1024

    def post(self, request):
        file = request.FILES.get("avatar")
        if not file:
            return Response({"detail": "avatar file is required."}, status=status.HTTP_400_BAD_REQUEST)
        ext = self.CONTENT_TYPES.get(file.content_type)
        if not ext:
            return Response(
                {"detail": "Only JPEG, PNG or WEBP images are allowed."}, status=status.HTTP_400_BAD_REQUEST
            )
        if file.size > self.MAX_SIZE:
            return Response({"detail": "Image must be smaller than 5MB."}, status=status.HTTP_400_BAD_REQUEST)

        path = f"avatars/{request.user.id}-{uuid_lib.uuid4().hex[:8]}.{ext}"
        saved_path = default_storage.save(path, file)
        request.user.avatar_url = request.build_absolute_uri(default_storage.url(saved_path))
        request.user.save(update_fields=["avatar_url"])
        return Response(UserSerializer(request.user).data)


class FriendListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = FriendSerializer
    pagination_class = None

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
        if data.get("user_id"):
            friend = User.objects.filter(id=data["user_id"]).first()
        if not friend and data.get("phone"):
            friend = User.objects.filter(phone=data["phone"]).first()
        if not friend and data.get("telegram_username"):
            friend = User.objects.filter(telegram_username=data["telegram_username"].lstrip("@")).first()
        if not friend and data.get("code"):
            code = data["code"].strip().upper()
            wallet = Wallet.objects.filter(paynet_id=code).select_related("user").first()
            if wallet:
                friend = wallet.user
        if not friend:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)
        if friend.id == request.user.id:
            return Response({"detail": "Cannot friend yourself."}, status=status.HTTP_400_BAD_REQUEST)

        existing = Friendship.objects.filter(user=request.user, friend=friend).first()
        if existing:
            return Response({"id": existing.id, "status": existing.status}, status=status.HTTP_200_OK)

        friendship = Friendship.objects.create(user=request.user, friend=friend)
        # Mutual pending row is not created — the incoming side is derived from
        # `friend=request.user, status=pending` in FriendPendingView.
        notify(
            friend,
            NotificationLog.NotificationType.FRIEND_REQUEST,
            requester_name=request.user.full_name or request.user.phone or "Someone",
        )
        return Response({"id": friendship.id, "status": friendship.status}, status=status.HTTP_201_CREATED)


class FriendPendingView(generics.ListAPIView):
    """Incoming friend requests waiting for the current user to accept."""

    permission_classes = [IsAuthenticated]
    serializer_class = FriendRequestSerializer
    pagination_class = None

    def get_queryset(self):
        return Friendship.objects.filter(
            friend=self.request.user, status=Friendship.Status.PENDING
        ).select_related("user").order_by("-created_at")


class FriendSearchView(generics.ListAPIView):
    """Search users by name/phone/telegram username/friend code — for adding new friends."""

    permission_classes = [IsAuthenticated]
    serializer_class = FriendSerializer
    pagination_class = None

    def get_queryset(self):
        q = self.request.query_params.get("q", "").strip()
        if len(q) < 2:
            return User.objects.none()
        return User.objects.filter(
            Q(full_name__icontains=q)
            | Q(phone__icontains=q)
            | Q(telegram_username__icontains=q)
            | Q(wallet__paynet_id__iexact=q)
        ).exclude(id=self.request.user.id)[:20]


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
        notify(
            friendship.user,
            NotificationLog.NotificationType.FRIEND_ACCEPTED,
            friend_name=request.user.full_name or request.user.phone or "Someone",
        )
        return Response({"status": "accepted"})
