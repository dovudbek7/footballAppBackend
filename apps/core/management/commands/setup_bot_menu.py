import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Register the Mini App menu button with BotFather via setChatMenuButton."

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN:
            raise CommandError("TELEGRAM_BOT_TOKEN is not set.")

        response = requests.post(
            f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/setChatMenuButton",
            json={
                "menu_button": {
                    "type": "web_app",
                    "text": "Open FutbolGo",
                    "web_app": {"url": settings.FRONTEND_URL},
                }
            },
            timeout=10,
        )
        response.raise_for_status()
        self.stdout.write(self.style.SUCCESS(f"Menu button set to {settings.FRONTEND_URL}"))
