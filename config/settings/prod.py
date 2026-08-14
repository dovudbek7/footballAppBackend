from decouple import config

from .base import *  # noqa: F401,F403

DEBUG = False
OTP_DEBUG_MODE = False

# No insecure fallback in prod — deploy must provide a real key.
SECRET_KEY = config("SECRET_KEY")

# Nginx terminates TLS and forwards the scheme; without this Django would
# loop on SECURE_SSL_REDIRECT behind the proxy.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 7
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# JSON only — no browsable API in prod.
REST_FRAMEWORK = {
    **REST_FRAMEWORK,  # noqa: F405
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
}
