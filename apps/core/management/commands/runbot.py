import asyncio
import logging

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

logging.basicConfig(level=logging.INFO)


class Command(BaseCommand):
    help = "Run the Sportify Telegram bot (aiogram, long polling) plus its scheduled jobs."

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN:
            raise CommandError("TELEGRAM_BOT_TOKEN is not set.")

        from aiogram import Bot
        from aiogram.client.default import DefaultBotProperties

        from bot.handlers import build_dispatcher
        from bot.scheduler import run_periodic_jobs

        async def main():
            bot = Bot(
                token=settings.TELEGRAM_BOT_TOKEN,
                default=DefaultBotProperties(parse_mode="HTML"),
            )
            dp = build_dispatcher()
            await run_periodic_jobs()
            self.stdout.write(self.style.SUCCESS("Bot polling started."))
            await dp.start_polling(bot)

        asyncio.run(main())
