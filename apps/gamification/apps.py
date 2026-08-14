from django.apps import AppConfig


class GamificationConfig(AppConfig):
    name = 'apps.gamification'

    def ready(self):
        from . import signals  # noqa: F401
