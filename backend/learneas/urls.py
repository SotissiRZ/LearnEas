from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/auth/", include("apps.accounts.urls")),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),

    path("api/catalog/", include("apps.catalog.urls")),
    path("api/enrollments/", include("apps.enrollments.urls")),
    path("api/payments/", include("apps.payments.urls")),
    path("api/reviews/", include("apps.reviews.urls")),
    path("api/faq/", include("apps.faq.urls")),
    path("api/chat/", include("apps.chat.urls")),
    path("api/", include("apps.formations.urls")),

    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
