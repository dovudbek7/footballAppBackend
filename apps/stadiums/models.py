import uuid

from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


class Amenity(models.Model):
    key = models.SlugField(max_length=32, unique=True)
    label = models.CharField(max_length=64)

    def __str__(self):
        return self.label


class Stadium(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=120)
    district = models.CharField(max_length=80)
    city = models.CharField(max_length=80)
    address = models.CharField(max_length=255)
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    main_image_url = models.URLField(blank=True)
    amenities = models.ManyToManyField(Amenity, blank=True, related_name="stadiums")

    base_price_per_hour = models.DecimalField(max_digits=8, decimal_places=2)
    base_slot_price = models.DecimalField(max_digits=8, decimal_places=2)

    owner_name = models.CharField(max_length=120, blank=True)
    owner_verified = models.BooleanField(default=False)
    owner_avatar_url = models.URLField(blank=True)

    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class StadiumImage(models.Model):
    stadium = models.ForeignKey(Stadium, related_name="gallery", on_delete=models.CASCADE)
    image_url = models.URLField()
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order"]


class StadiumSlotTemplate(TimeStampedModel):
    """Recurring slot definition, expanded into concrete Match rows by a management command."""

    WEEKDAY_CHOICES = [(i, name) for i, name in enumerate(
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    )]

    stadium = models.ForeignKey(Stadium, related_name="slot_templates", on_delete=models.CASCADE)
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAY_CHOICES, null=True, blank=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    capacity = models.PositiveSmallIntegerField(default=10)
    price_per_seat_override = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def price_per_seat(self):
        return self.price_per_seat_override or self.stadium.base_slot_price


class Review(TimeStampedModel):
    stadium = models.ForeignKey(Stadium, related_name="reviews", on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField()
    text = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["stadium", "author"], name="one_review_per_user_per_stadium"),
            models.CheckConstraint(condition=models.Q(rating__gte=1) & models.Q(rating__lte=5), name="review_rating_range"),
        ]


class FavoriteStadium(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="favorite_stadiums", on_delete=models.CASCADE)
    stadium = models.ForeignKey(Stadium, related_name="favorited_by", on_delete=models.CASCADE)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "stadium"], name="unique_favorite")]
