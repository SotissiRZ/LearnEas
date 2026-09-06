from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from apps.accounts.views import CookieTokenRefreshView

admin.site.site_header = "KalanPro · Administration"
admin.site.site_title = "KalanPro Admin"
admin.site.index_title = "Centre de contrôle KalanPro"

def health_live(request):
    # Liveness : ne dépend d'aucun service externe. Un orchestrateur ne doit pas
    # redémarrer Django simplement parce que PostgreSQL/Redis est momentanément indisponible.
    return JsonResponse({"status": "ok"})


def health_ready(request):
    checks = {"database": "error", "cache": "error"}
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = "ok"
        cache.set("healthcheck", "ok", 5)
        if cache.get("healthcheck") != "ok":
            raise RuntimeError("cache")
        checks["cache"] = "ok"
    except Exception:
        return JsonResponse({"status": "error", "checks": checks}, status=503)
    return JsonResponse({"status": "ok", "checks": checks})


def health(request):
    # Alias historique conservé pour Docker/Railway.
    return health_ready(request)

urlpatterns = [
    path("api/health/", health),
    path("api/health/live/", health_live),
    path("api/health/ready/", health_ready),
    path("admin/", admin.site.urls),

    path("api/", include("apps.common.urls")),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/auth/token/refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),

    path("api/catalog/", include("apps.catalog.urls")),
    path("api/enrollments/", include("apps.enrollments.urls")),
    path("api/payments/", include("apps.payments.urls")),
    path("api/reviews/", include("apps.reviews.urls")),
    path("api/faq/", include("apps.faq.urls")),
    path("api/chat/", include("apps.chat.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/support/", include("apps.support.urls")),
    path("api/projects/", include("apps.projects.urls")),
    path("api/opportunities/", include("apps.opportunities.urls")),
    path("api/discovery/", include("apps.discovery.urls")),
    path("api/analytics/", include("apps.analytics.urls")),
    path("api/ai/", include("apps.assistant_ai.urls")),
    path("api/", include("apps.formations.urls")),

]

if settings.DEBUG:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
