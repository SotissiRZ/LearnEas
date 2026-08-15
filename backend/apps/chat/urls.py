from rest_framework.routers import DefaultRouter
from .views import ChatMessageViewSet

router = DefaultRouter()
router.register("messages", ChatMessageViewSet, basename="chat-message")

urlpatterns = router.urls
