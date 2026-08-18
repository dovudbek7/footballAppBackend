from django.db import transaction
from django.db.models import Avg
from django.utils import timezone

from apps.bookings.models import ACTIVE_PAYMENT_STATUSES, Booking
from apps.notifications.models import NotificationLog
from apps.notifications.services import notify

from .models import DEFAULT_SKILLS, Badge, UserBadge, UserSeasonScore, UserSkillRating

POINTS_PER_MATCH = 10
POINTS_PER_WIN = 15
POINTS_PER_MOTM = 25

IRONMAN_MATCHES_THRESHOLD = 10
EARLYBIRD_LEAD_TIME_DAYS = 2


def _timesince_label(dt) -> str:
    delta = timezone.now() - dt
    days = delta.days
    if days >= 1:
        return f"{days}d ago"
    hours = delta.seconds // 3600
    if hours >= 1:
        return f"{hours}h ago"
    return f"{max(delta.seconds // 60, 1)}m ago"


def compute_profile_stats(user) -> dict:
    """Shared by the self /profile/stats endpoint and the friend-profile view."""
    bookings = Booking.objects.filter(user=user, payment_status__in=ACTIVE_PAYMENT_STATUSES)
    matches_played = bookings.count()
    wins = bookings.filter(personal_result=Booking.Result.WON).count()
    motm_awards = bookings.filter(is_motm=True).count()
    avg_rating = bookings.aggregate(avg=Avg("rating"))["avg"] or 0

    return {
        "name": user.full_name,
        "bio": user.bio,
        "position": user.position,
        "city": user.city,
        "avatar": user.avatar_url,
        "tier": user.experience_level,
        "matches_played": matches_played,
        "win_rate": round(wins / matches_played * 100, 1) if matches_played else 0.0,
        "motm_awards": motm_awards,
        "avg_rating": round(float(avg_rating), 1),
        "stats": user.skill_ratings.all(),
    }


def compute_recent_activity(user, limit: int = 20) -> list:
    bookings = (
        Booking.objects.filter(
            user=user,
            payment_status__in=ACTIVE_PAYMENT_STATUSES,
            match__status="finished",
        )
        .select_related("match", "match__stadium")
        .order_by("-updated_at")[:limit]
    )
    items = []
    for booking in bookings:
        detail_parts = []
        if booking.rating is not None:
            detail_parts.append(f"{booking.rating} Rating")
        if booking.goals or booking.assists:
            detail_parts.append(f"{booking.goals or 0} Goal, {booking.assists or 0} Assists")
        items.append(
            {
                "id": booking.id,
                "result": booking.personal_result or "-",
                "ago": _timesince_label(booking.updated_at),
                "stadium": booking.match.stadium.name,
                "detail": " • ".join(detail_parts),
            }
        )
    return items


def seed_default_skills(user) -> None:
    base = {"Beginner": 40, "Amateur": 60, "PRO": 80}.get(user.experience_level, 50)
    for key, label in DEFAULT_SKILLS:
        UserSkillRating.objects.get_or_create(user=user, key=key, defaults={"label": label, "value": base})


def _points_for_booking(booking: Booking) -> int:
    points = POINTS_PER_MATCH
    if booking.personal_result == Booking.Result.WON:
        points += POINTS_PER_WIN
    if booking.is_motm:
        points += POINTS_PER_MOTM
    return points


@transaction.atomic
def apply_match_result_scoring(match) -> None:
    period = match.date.strftime("%Y-%m")
    bookings = match.bookings.filter(payment_status__in=ACTIVE_PAYMENT_STATUSES).select_related("user")

    for booking in bookings:
        region = booking.user.region or ""
        score, _ = UserSeasonScore.objects.get_or_create(
            user=booking.user, period=period, region=region, defaults={"points": 0}
        )
        score.points += _points_for_booking(booking)
        score.save(update_fields=["points"])
        _check_badges(booking.user)


def _unlock(user, code: str) -> None:
    badge = Badge.objects.filter(code=code, is_active=True).first()
    if not badge:
        return
    user_badge, created = UserBadge.objects.get_or_create(user=user, badge=badge)
    if created or not user_badge.unlocked_at:
        user_badge.unlocked_at = timezone.now()
        user_badge.save(update_fields=["unlocked_at"])
        notify(user, NotificationLog.NotificationType.BADGE_UNLOCKED, badge_title=badge.title)


def _check_badges(user) -> None:
    active_bookings = Booking.objects.filter(user=user, payment_status__in=ACTIVE_PAYMENT_STATUSES)

    if active_bookings.count() >= IRONMAN_MATCHES_THRESHOLD:
        _unlock(user, "ironman")

    last_booking = active_bookings.order_by("-created_at").first()
    if last_booking:
        match = last_booking.match
        lead_time = match.date - last_booking.created_at.date()
        if lead_time.days >= EARLYBIRD_LEAD_TIME_DAYS:
            _unlock(user, "earlybird")
        if (last_booking.goals or 0) >= 3:
            _unlock(user, "hattrick")
        if (last_booking.assists or 0) >= 3:
            _unlock(user, "playmaker")
