from django.urls import path
from .views import PrivateMediaView
urlpatterns = [path("media/private/", PrivateMediaView.as_view(), name="private-media")]
