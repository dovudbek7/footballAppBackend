"""In-process periodic jobs for the bot container.

MVP deliberately has no Celery/Redis (see the plan's infra rationale) — this is
the one always-on process, so APScheduler running inside it covers the few
genuinely time-driven needs: match reminders and split-pay seat expiry.
"""

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from asgiref.sync import sync_to_async
from django.utils import timezone

logger = logging.getLogger(__name__)

REMINDER_LEAD_TIME = timedelta(minutes=60)
REMINDER_WINDOW = timedelta(minutes=10)


def _send_match_reminders() -> None:
    from apps.bookings.models import ACTIVE_PAYMENT_STATUSES, Match
    from apps.notifications.models import NotificationLog
    from apps.notifications.services import notify

    now = timezone.now()
    window_start = now + REMINDER_LEAD_TIME
    window_end = window_start + REMINDER_WINDOW

    matches = Match.objects.filter(status=Match.Status.CONFIRMED, reminder_sent=False).select_related("stadium")
    for match in matches:
        starts_at = timezone.make_aware(datetime.combine(match.date, match.start_time))
        if not (window_start <= starts_at <= window_end):
            continue
        for booking in match.bookings.filter(payment_status__in=ACTIVE_PAYMENT_STATUSES).select_related("user"):
            notify(
                booking.user,
                NotificationLog.NotificationType.MATCH_REMINDER,
                stadium_name=match.stadium.name,
                minutes=int((starts_at - now).total_seconds() // 60),
            )
        match.reminder_sent = True
        match.save(update_fields=["reminder_sent"])


def _expire_pending_split_bookings() -> None:
    from apps.bookings.models import Booking
    from apps.bookings.services import refresh_match_status
    from apps.notifications.models import NotificationLog
    from apps.notifications.services import notify

    now = timezone.now()
    pending = Booking.objects.filter(payment_status=Booking.PaymentStatus.PENDING).select_related(
        "match", "match__stadium", "user", "invited_by"
    )
    for booking in pending:
        starts_at = timezone.make_aware(datetime.combine(booking.match.date, booking.match.start_time))
        if now < starts_at:
            continue
        booking.payment_status = Booking.PaymentStatus.CANCELED
        booking.canceled_at = now
        booking.save(update_fields=["payment_status", "canceled_at"])
        refresh_match_status(booking.match)
        if booking.invited_by_id and booking.invited_by_id != booking.user_id:
            notify(
                booking.invited_by,
                NotificationLog.NotificationType.WAITLIST_FILLED,
                stadium_name=booking.match.stadium.name,
                date=f"seat for {booking.user.full_name or booking.user.phone} expired unpaid",
            )


async def run_periodic_jobs() -> None:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(sync_to_async(_send_match_reminders), "interval", minutes=5)
    scheduler.add_job(sync_to_async(_expire_pending_split_bookings), "interval", minutes=5)
    scheduler.start()
    logger.info("Scheduler started: match reminders + split-pay expiry every 5 min.")
