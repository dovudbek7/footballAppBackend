from bot.telegram_client import send_message

from .models import NotificationLog

_TEMPLATES = {
    NotificationLog.NotificationType.OTP_CODE: "Your Sportify login code: <b>{code}</b> (valid 5 min).",
    NotificationLog.NotificationType.TELEGRAM_LINK: "Telegram linked to Sportify. Sending your login code now...",
    NotificationLog.NotificationType.BOOKING_CONFIRMED: (
        "✅ Booking confirmed: {stadium_name} on {date} at {time}."
    ),
    NotificationLog.NotificationType.SPLIT_REQUEST: (
        "⚽ {organizer_name} invited you to split-pay a seat at {stadium_name} "
        "on {date} at {time} — your share: ${amount}."
    ),
    NotificationLog.NotificationType.MATCH_REMINDER: (
        "⏰ Reminder: your match at {stadium_name} starts in {minutes} min."
    ),
    NotificationLog.NotificationType.WAITLIST_FILLED: (
        "🏁 Your match at {stadium_name} on {date} is now full — confirmed!"
    ),
    NotificationLog.NotificationType.SPLIT_EXPIRED: (
        "⌛ The split-pay seat you reserved for {friend_name} at {stadium_name} expired unpaid and was released."
    ),
    NotificationLog.NotificationType.BADGE_UNLOCKED: "🏆 Badge unlocked: {badge_title}!",
    NotificationLog.NotificationType.TOPUP_APPROVED: "💰 Top-up approved: ${amount} added to your wallet.",
    NotificationLog.NotificationType.FRIEND_REQUEST: (
        "🤝 {requester_name} sent you a friend request."
    ),
    NotificationLog.NotificationType.FRIEND_ACCEPTED: (
        "🤝 {friend_name} accepted your friend request."
    ),
    NotificationLog.NotificationType.MATCH_INVITE: (
        "⚽ {organizer_name} invited you to a match at {stadium_name} on {date} at {time}."
    ),
}


def render_text(notification_type: str, **context) -> str:
    template = _TEMPLATES.get(notification_type, "{message}")
    return template.format(**context)


def notify(user, notification_type: str, **context) -> NotificationLog:
    text = render_text(notification_type, **context)

    if not user.telegram_id:
        return NotificationLog.objects.create(
            user=user,
            telegram_id=None,
            type=notification_type,
            text=text,
            payload=context,
            status=NotificationLog.Status.SKIPPED,
            error_text="User has no linked telegram_id",
        )

    sent = send_message(user.telegram_id, text)
    return NotificationLog.objects.create(
        user=user,
        telegram_id=user.telegram_id,
        type=notification_type,
        text=text,
        payload=context,
        status=NotificationLog.Status.SENT if sent else NotificationLog.Status.FAILED,
    )
