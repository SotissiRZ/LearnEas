from rest_framework.routers import DefaultRouter
from .views import SupportTicketViewSet, ModerationReportViewSet

router = DefaultRouter()
router.register("tickets", SupportTicketViewSet, basename="support-ticket")
router.register("reports", ModerationReportViewSet, basename="moderation-report")

urlpatterns = router.urls
