from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.bookings.models import Match
from apps.stadiums.models import StadiumSlotTemplate


class Command(BaseCommand):
    help = "Expand active StadiumSlotTemplates into concrete Match rows for the next N days."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=14)

    def handle(self, *args, **options):
        days = options["days"]
        today = timezone.now().date()
        created = 0

        templates = StadiumSlotTemplate.objects.filter(is_active=True).select_related("stadium")
        for offset in range(days):
            day = today + timedelta(days=offset)
            for template in templates:
                if template.weekday is not None and template.weekday != day.weekday():
                    continue
                _, was_created = Match.objects.get_or_create(
                    stadium=template.stadium,
                    date=day,
                    start_time=template.start_time,
                    defaults={
                        "slot_template": template,
                        "end_time": template.end_time,
                        "capacity": template.capacity,
                        "price_per_seat": template.price_per_seat(),
                    },
                )
                created += was_created

        self.stdout.write(self.style.SUCCESS(f"Created {created} new matches over the next {days} days."))
