from django.urls import path
from .views import HlsMediaView, PrivateMediaView
urlpatterns = [
    path("media/private/", PrivateMediaView.as_view(), name="private-media"),
    path("media/hls/", HlsMediaView.as_view(), name="hls-media"),
]
