from django.urls import path
from .views import HlsMediaView, PrivateMediaView, ClientErrorTelemetryView
urlpatterns = [
    path("telemetry/client-error/", ClientErrorTelemetryView.as_view(), name="client-error-telemetry"),
    path("media/private/", PrivateMediaView.as_view(), name="private-media"),
    path("media/hls/", HlsMediaView.as_view(), name="hls-media"),
]
