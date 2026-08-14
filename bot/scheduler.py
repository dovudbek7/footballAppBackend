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


def _send_match_reminders() -> None:
    from apps.bookings.models import ACTIVE_PAYMENT_STATUSES, Match
    from apps.notifications.models import NotificationLog
    from apps.notifications.services import notify

    now = timezone.now()
    today = now.date()

    # Bounded queryset: only today/tomorrow can be within the 60-min lead window,
    # so stale unreminded matches never accumulate in the scan.
    matches = Match.objects.filter(
        status=Match.Status.CONFIRMED,
        reminder_sent=False,
        date__gte=today,
        date__lte=today + timedelta(days=1),
    ).select_related("stadium")
    for match in matches:
        starts_at = timezone.make_aware(datetime.combine(match.date, match.start_time))
        if starts_at <= now:
            # Kickoff already passed — mark handled so it drops out of the scan.
            match.reminder_sent = True
            match.save(update_fields=["reminder_sent"])
            continue
        if starts_at - now > REMINDER_LEAD_TIME:
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
                NotificationLog.NotificationType.SPLIT_EXPIRED,
                friend_name=booking.user.full_name or booking.user.phone or "your friend",
                stadium_name=booking.match.stadium.name,
            )


def _generate_upcoming_matches() -> None:
    """Keep the next 14 days of matches materialized from slot templates."""
    from django.core.management import call_command

    try:
        call_command("generate_matches", days=14)
    except Exception:
        logger.exception("generate_matches failed")


async def run_periodic_jobs() -> None:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(sync_to_async(_send_match_reminders), "interval", minutes=5)
    scheduler.add_job(sync_to_async(_expire_pending_split_bookings), "interval", minutes=5)
    scheduler.add_job(sync_to_async(_generate_upcoming_matches), "interval", hours=12)
    # Startupda ham bir marta — deploydan keyin darhol slotlar paydo bo'lsin
    await sync_to_async(_generate_upcoming_matches)()
    scheduler.start()
    logger.info("Scheduler started: reminders + split expiry (5 min), match generation (12h).")
