import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "learneas.settings")

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import OriginValidator
from django.conf import settings
from django.core.asgi import get_asgi_application

# Initialise d'abord Django/app registry avant d'importer un routing qui charge des modèles.
django_asgi_app = get_asgi_application()

from apps.formations.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": OriginValidator(
        URLRouter(websocket_urlpatterns),
        settings.REALTIME_ALLOWED_ORIGINS,
    ),
})
