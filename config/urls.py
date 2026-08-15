from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.views import health_check

urlpatterns = [
    path("admin/", admin.site.urls),
    path("panel/", include("apps.panel.urls")),
    path("api/health", health_check),
    path("api/schema", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs", SpectacularSwaggerView.as_view(url_name="schema")),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.stadiums.urls")),
    path("api/", include("apps.bookings.urls")),
    path("api/", include("apps.wallet.urls")),
    path("api/", include("apps.gamification.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
