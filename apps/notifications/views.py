from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DeviceToken, NotificationLog
from .serializers import DeviceTokenRegisterSerializer, DeviceTokenSerializer, NotificationSerializer


class NotificationListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def get_queryset(self):
        return NotificationLog.objects.filter(user=self.request.user)


class NotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = NotificationLog.objects.filter(user=request.user, read_at__isnull=True).count()
        return Response({"count": count})


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = get_object_or_404(NotificationLog, pk=pk, user=request.user)
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at"])
        return Response(NotificationSerializer(notification).data)


class NotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        NotificationLog.objects.filter(user=request.user, read_at__isnull=True).update(read_at=timezone.now())
        return Response(status=status.HTTP_204_NO_CONTENT)


class DeviceTokenRegisterView(APIView):
    """Registers (or upserts) an FCM device token for the authenticated user.

    Upserts by `token` — re-registering the same token just refreshes its
    ownership/platform and re-activates it. When `device_id` is provided and
    the same physical device previously registered under a different token
    (e.g. the OS rotated the FCM token), the stale token for that device is
    deactivated so we don't keep sending pushes to a dead token.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DeviceTokenRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]
        platform = serializer.validated_data["platform"]
        device_id = serializer.validated_data.get("device_id", "")

        if device_id:
            DeviceToken.objects.filter(user=request.user, device_id=device_id).exclude(token=token).update(
                is_active=False
            )

        device_token, _created = DeviceToken.objects.update_or_create(
            token=token,
            defaults={
                "user": request.user,
                "platform": platform,
                "device_id": device_id,
                "is_active": True,
            },
        )
        return Response(DeviceTokenSerializer(device_token).data, status=status.HTTP_200_OK)


class DeviceTokenUnregisterView(APIView):
    """Deactivates a device token, e.g. on logout, so we stop pushing to it."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        token = request.data.get("token")
        if not token:
            return Response({"detail": "token is required"}, status=status.HTTP_400_BAD_REQUEST)
        updated = DeviceToken.objects.filter(user=request.user, token=token).update(is_active=False)
        if not updated:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(status=status.HTTP_204_NO_CONTENT)
