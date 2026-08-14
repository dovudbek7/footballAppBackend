from django.apps import AppConfig


class WalletConfig(AppConfig):
    name = 'apps.wallet'

    def ready(self):
        from . import signals  # noqa: F401
