from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.bookings.models import MatchResult

from . import services


@receiver(post_save, sender=MatchResult)
def score_match_on_result(sender, instance, created, **kwargs):
    # Only score the first submission — editing/resubmitting a result must not
    # award leaderboard points a second time.
    if created:
        services.apply_match_result_scoring(instance.match)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def seed_skills_on_onboard(sender, instance, **kwargs):
    if instance.is_onboarded:
        services.seed_default_skills(instance)
