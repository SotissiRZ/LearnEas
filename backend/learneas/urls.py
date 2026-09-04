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

def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        cache.set("healthcheck", "ok", 5)
        if cache.get("healthcheck") != "ok": raise RuntimeError("cache")
        return JsonResponse({"status": "ok"})
    except Exception:
        return JsonResponse({"status": "error"}, status=503)

urlpatterns = [
    path("api/health/", health),
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
    path("api/projects/", include("apps.projects.urls")),
    path("api/opportunities/", include("apps.opportunities.urls")),
    path("api/ai/", include("apps.assistant_ai.urls")),
    path("api/", include("apps.formations.urls")),

]

if settings.DEBUG:
    urlpatterns += [
        path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
        path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
