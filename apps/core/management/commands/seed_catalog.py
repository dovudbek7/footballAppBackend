from django.core.management.base import BaseCommand

from apps.gamification.models import Badge
from apps.stadiums.models import Amenity
from apps.wallet.models import ExchangeRate, PaymentMethod

AMENITIES = [
    ("parking", "Parking"),
    ("changing_room", "Changing room"),
    ("shower", "Shower"),
    ("floodlights", "Floodlights"),
    ("cafe", "Cafe"),
    ("water", "Drinking water"),
]

PAYMENT_METHODS = [
    ("click", "Click", "Pay instantly via Click", PaymentMethod.Icon.CLICK, 1),
    ("payme", "Payme", "Pay instantly via Payme", PaymentMethod.Icon.PAYME, 2),
    ("card", "Linked card", "Charge a saved bank card", PaymentMethod.Icon.CARD, 3),
    ("kiosk", "Paynet kiosk", "Top up in cash at any Paynet kiosk", PaymentMethod.Icon.KIOSK, 4),
]

BADGES = [
    ("hattrick", "Hattrick Hero", "Score 3+ goals in a single match", Badge.Icon.HATTRICK),
    ("playmaker", "Playmaker", "Register 3+ assists in a single match", Badge.Icon.PLAYMAKER),
    ("ironman", "Ironman", "Play 10+ matches", Badge.Icon.IRONMAN),
    ("earlybird", "Early Bird", "Book a match 2+ days in advance", Badge.Icon.EARLYBIRD),
]


class Command(BaseCommand):
    help = "Seed static catalog data: amenities, payment methods, badges, default exchange rate."

    def handle(self, *args, **options):
        for key, label in AMENITIES:
            Amenity.objects.get_or_create(key=key, defaults={"label": label})

        for key, name, description, icon, sort_order in PAYMENT_METHODS:
            PaymentMethod.objects.get_or_create(
                key=key, defaults={"name": name, "description": description, "icon": icon, "sort_order": sort_order}
            )

        for code, title, requirement, icon in BADGES:
            Badge.objects.get_or_create(
                code=code, defaults={"title": title, "requirement_text": requirement, "icon": icon}
            )

        if not ExchangeRate.objects.exists():
            ExchangeRate.objects.create(currency_pair="USD_UZS", rate=12700)

        self.stdout.write(self.style.SUCCESS("Catalog seeded."))
