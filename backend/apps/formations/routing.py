from django.urls import re_path

from .consumers import FormationRealtimeConsumer

websocket_urlpatterns = [
    re_path(r"^ws/sessions/(?P<session_id>\d+)/$", FormationRealtimeConsumer.as_asgi()),
]
