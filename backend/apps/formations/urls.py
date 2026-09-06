from rest_framework.routers import DefaultRouter
from .views import (
    InteractiveFormationViewSet, FormationSessionViewSet, MyFormationsViewSet,
    MentorshipOfferingViewSet, MentorshipSlotViewSet, MentorshipBookingViewSet,
    MentorshipPackViewSet, MentorshipPassViewSet, MentorshipAvailabilityRuleViewSet,
)

router = DefaultRouter()
router.register("formations", InteractiveFormationViewSet, basename="formation")
router.register("sessions", FormationSessionViewSet, basename="formation-session")
router.register("my-formations", MyFormationsViewSet, basename="my-formation")
router.register("mentorship/offerings", MentorshipOfferingViewSet, basename="mentorship-offering")
router.register("mentorship/slots", MentorshipSlotViewSet, basename="mentorship-slot")
router.register("mentorship/bookings", MentorshipBookingViewSet, basename="mentorship-booking")
router.register("mentorship/packs", MentorshipPackViewSet, basename="mentorship-pack")
router.register("mentorship/passes", MentorshipPassViewSet, basename="mentorship-pass")
router.register("mentorship/availability-rules", MentorshipAvailabilityRuleViewSet, basename="mentorship-availability-rule")

urlpatterns = router.urls
