"""Seed a starter set of Tashkent stadiums with recurring slot templates.

Idempotent: keyed on stadium name. Run `generate_matches` afterwards to expand
the templates into bookable Match rows.
"""

from datetime import time
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.stadiums.models import Amenity, Stadium, StadiumImage, StadiumSlotTemplate

UNSPLASH = "https://images.unsplash.com"

STADIUMS = [
    {
        "name": "Chilonzor Arena",
        "district": "Chilonzor",
        "city": "Tashkent",
        "address": "Chilonzor 19-mavze, Tashkent",
        "main_image_url": f"{UNSPLASH}/photo-1459865264687-595d652de67e?w=1200&q=80",
        "gallery": [
            f"{UNSPLASH}/photo-1459865264687-595d652de67e?w=1200&q=80",
            f"{UNSPLASH}/photo-1529900748604-07564a03e7a6?w=1200&q=80",
        ],
        "base_price_per_hour": Decimal("40"),
        "base_slot_price": Decimal("5"),
        "owner_name": "Bekzod Rakhimov",
        "owner_verified": True,
        "amenities": ["parking", "shower", "floodlights", "water"],
        "capacity": 12,
        "slots": [(18, 19), (19, 20), (20, 21), (21, 22)],
    },
    {
        "name": "Yunusobod Indoor",
        "district": "Yunusobod",
        "city": "Tashkent",
        "address": "Yunusobod 11-mavze, Tashkent",
        "main_image_url": f"{UNSPLASH}/photo-1524015368236-bbf6f72545b6?w=1200&q=80",
        "gallery": [
            f"{UNSPLASH}/photo-1524015368236-bbf6f72545b6?w=1200&q=80",
            f"{UNSPLASH}/photo-1518604666860-9ed391f76460?w=1200&q=80",
        ],
        "base_price_per_hour": Decimal("32"),
        "base_slot_price": Decimal("4"),
        "owner_name": "Sherzod Aliyev",
        "owner_verified": True,
        "amenities": ["parking", "changing_room", "floodlights", "cafe"],
        "capacity": 10,
        "slots": [(19, 20), (20, 21), (21, 22), (22, 23)],
    },
    {
        "name": "Mirzo Ulug'bek Turf",
        "district": "Mirzo Ulug'bek",
        "city": "Tashkent",
        "address": "Buyuk Ipak Yo'li, Tashkent",
        "main_image_url": f"{UNSPLASH}/photo-1575361204480-aadea25e6e68?w=1200&q=80",
        "gallery": [
            f"{UNSPLASH}/photo-1575361204480-aadea25e6e68?w=1200&q=80",
            f"{UNSPLASH}/photo-1431324155629-1a6deb1dec8d?w=1200&q=80",
        ],
        "base_price_per_hour": Decimal("36"),
        "base_slot_price": Decimal("4.50"),
        "owner_name": "Aziz Karimov",
        "owner_verified": False,
        "amenities": ["shower", "floodlights", "water", "cafe"],
        "capacity": 12,
        "slots": [(18, 19), (20, 21), (21, 22)],
    },
    {
        "name": "Sergeli Sport Park",
        "district": "Sergeli",
        "city": "Tashkent",
        "address": "Sergeli 8-mavze, Tashkent",
        "main_image_url": f"{UNSPLASH}/photo-1556056504-5c7696c4c28d?w=1200&q=80",
        "gallery": [
            f"{UNSPLASH}/photo-1556056504-5c7696c4c28d?w=1200&q=80",
        ],
        "base_price_per_hour": Decimal("28"),
        "base_slot_price": Decimal("3.50"),
        "owner_name": "Jasur Toshmatov",
        "owner_verified": True,
        "amenities": ["parking", "changing_room", "water"],
        "capacity": 10,
        "slots": [(19, 20), (20, 21)],
    },
]


class Command(BaseCommand):
    help = "Seed demo Tashkent stadiums with recurring slot templates (idempotent)."

    def handle(self, *args, **options):
        created_count = 0
        for spec in STADIUMS:
            stadium, created = Stadium.objects.get_or_create(
                name=spec["name"],
                defaults={
                    "district": spec["district"],
                    "city": spec["city"],
                    "address": spec["address"],
                    "main_image_url": spec["main_image_url"],
                    "base_price_per_hour": spec["base_price_per_hour"],
                    "base_slot_price": spec["base_slot_price"],
                    "owner_name": spec["owner_name"],
                    "owner_verified": spec["owner_verified"],
                },
            )
            if not created:
                continue
            created_count += 1

            stadium.amenities.set(Amenity.objects.filter(key__in=spec["amenities"]))
            for index, url in enumerate(spec["gallery"]):
                StadiumImage.objects.create(stadium=stadium, image_url=url, sort_order=index)
            for start_hour, end_hour in spec["slots"]:
                StadiumSlotTemplate.objects.create(
                    stadium=stadium,
                    weekday=None,  # har kuni
                    start_time=time(start_hour % 24, 0),
                    end_time=time(end_hour % 24, 0),
                    capacity=spec["capacity"],
                )

        self.stdout.write(self.style.SUCCESS(f"Demo stadiums seeded ({created_count} new)."))
