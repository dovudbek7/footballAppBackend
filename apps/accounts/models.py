import secrets
import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, phone=None, telegram_id=None, password=None, **extra_fields):
        if not phone and not telegram_id:
            raise ValueError("A user requires a phone number or a telegram_id")
        user = self.model(phone=phone, telegram_id=telegram_id, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, phone=None, telegram_id=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(phone, telegram_id, password, **extra_fields)

    def create_superuser(self, phone=None, telegram_id=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_onboarded", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(phone, telegram_id, password, **extra_fields)


class ExperienceLevel(models.TextChoices):
    BEGINNER = "Beginner", "Beginner"
    AMATEUR = "Amateur", "Amateur"
    PRO = "PRO", "PRO"


class Language(models.TextChoices):
    UZBEK = "uz", "O'zbekcha"
    RUSSIAN = "ru", "Русский"
    ENGLISH = "en", "English"


class Role(models.TextChoices):
    PLAYER = "player", "Player"
    HOST = "host", "Host"
    ORGANIZER = "organizer", "Organizer"


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    phone = models.CharField(max_length=20, unique=True, null=True, blank=True)
    telegram_id = models.BigIntegerField(unique=True, null=True, blank=True)
    telegram_username = models.CharField(max_length=64, blank=True)

    full_name = models.CharField(max_length=120, blank=True)
    avatar_url = models.URLField(blank=True)
    region = models.CharField(max_length=64, blank=True)
    city = models.CharField(max_length=64, blank=True)
    position = models.CharField(max_length=64, blank=True)
    experience_level = models.CharField(
        max_length=16, choices=ExperienceLevel.choices, default=ExperienceLevel.AMATEUR
    )
    language = models.CharField(max_length=8, choices=Language.choices, default=Language.UZBEK)

    is_onboarded = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.PLAYER)

    objects = UserManager()

    USERNAME_FIELD = "phone"
    REQUIRED_FIELDS = []

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(phone__isnull=False) | models.Q(telegram_id__isnull=False),
                name="user_has_phone_or_telegram_id",
            )
        ]

    def __str__(self):
        return self.full_name or self.phone or str(self.telegram_id) or str(self.id)


def generate_otp_code():
    return f"{secrets.randbelow(1_000_000):06d}"


def generate_link_token():
    return secrets.token_urlsafe(24)


class OTPCode(TimeStampedModel):
    class Purpose(models.TextChoices):
        LOGIN = "login", "Login"

    phone = models.CharField(max_length=20, db_index=True)
    code = models.CharField(max_length=6, default=generate_otp_code)
    purpose = models.CharField(max_length=16, choices=Purpose.choices, default=Purpose.LOGIN)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)

    MAX_ATTEMPTS = 5
    TTL_SECONDS = 5 * 60

    @classmethod
    def issue(cls, phone: str) -> "OTPCode":
        return cls.objects.create(
            phone=phone,
            expires_at=timezone.now() + timezone.timedelta(seconds=cls.TTL_SECONDS),
        )

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def is_consumed(self) -> bool:
        return self.consumed_at is not None

    def verify(self, code: str) -> bool:
        if self.is_expired or self.is_consumed or self.attempts >= self.MAX_ATTEMPTS:
            return False
        self.attempts += 1
        self.save(update_fields=["attempts"])
        if not secrets.compare_digest(self.code, code):
            return False
        self.consumed_at = timezone.now()
        self.save(update_fields=["consumed_at"])
        return True


class TelegramLinkToken(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        LINKED = "linked", "Linked"
        EXPIRED = "expired", "Expired"

    token = models.CharField(max_length=48, unique=True, default=generate_link_token)
    phone = models.CharField(max_length=20, db_index=True)
    telegram_id = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    expires_at = models.DateTimeField()
    otp_code = models.ForeignKey(OTPCode, null=True, blank=True, on_delete=models.SET_NULL)

    TTL_SECONDS = 10 * 60

    @classmethod
    def issue(cls, phone: str) -> "TelegramLinkToken":
        cls.objects.filter(phone=phone, status=cls.Status.PENDING).update(status=cls.Status.EXPIRED)
        return cls.objects.create(
            phone=phone,
            expires_at=timezone.now() + timezone.timedelta(seconds=cls.TTL_SECONDS),
        )

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    def deep_link(self, bot_username: str) -> str:
        return f"https://t.me/{bot_username}?start={self.token}"


class Friendship(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"

    user = models.ForeignKey(User, related_name="friendships_sent", on_delete=models.CASCADE)
    friend = models.ForeignKey(User, related_name="friendships_received", on_delete=models.CASCADE)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "friend"], name="unique_friendship_pair"),
            models.CheckConstraint(condition=~models.Q(user=models.F("friend")), name="friendship_not_self"),
        ]
