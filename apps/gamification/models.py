from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class UserSkillRating(TimeStampedModel):
    """Radar-chart axis. No per-match stat source exists yet, so these are
    self-declared at onboarding (seeded from experience_level) and user-editable."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="skill_ratings", on_delete=models.CASCADE)
    key = models.SlugField(max_length=32)
    label = models.CharField(max_length=32)
    value = models.PositiveSmallIntegerField(default=50)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "key"], name="unique_skill_per_user")]
        ordering = ["key"]


DEFAULT_SKILLS = [
    ("pace", "Pace"),
    ("shooting", "Shooting"),
    ("passing", "Passing"),
    ("defense", "Defense"),
    ("physical", "Physical"),
]


class Badge(models.Model):
    class Icon(models.TextChoices):
        HATTRICK = "hattrick", "Hattrick"
        PLAYMAKER = "playmaker", "Playmaker"
        IRONMAN = "ironman", "Ironman"
        EARLYBIRD = "earlybird", "Earlybird"

    code = models.SlugField(max_length=32, unique=True)
    title = models.CharField(max_length=64)
    requirement_text = models.CharField(max_length=255)
    icon = models.CharField(max_length=16, choices=Icon.choices)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class UserBadge(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="badges", on_delete=models.CASCADE)
    badge = models.ForeignKey(Badge, on_delete=models.CASCADE)
    unlocked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "badge"], name="unique_user_badge")]


class UserSeasonScore(TimeStampedModel):
    """Denormalized leaderboard points — recomputing from raw match history on every
    request scoped by month+region isn't worth it at this scale; updated via signal."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="season_scores", on_delete=models.CASCADE)
    period = models.CharField(max_length=7)  # "2026-08"
    region = models.CharField(max_length=64, blank=True)
    points = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "period", "region"], name="unique_season_score")
        ]
        indexes = [models.Index(fields=["period", "region", "-points"])]
