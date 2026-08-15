from rest_framework.routers import DefaultRouter
from .views import FAQViewSet

router = DefaultRouter()
router.register("", FAQViewSet, basename="faq")

urlpatterns = router.urls
