from rest_framework.routers import DefaultRouter
from .views import EmployerProfileViewSet, CandidateProfileViewSet, OpportunityViewSet, ApplicationViewSet, TalentViewSet

router = DefaultRouter()
router.register("employer-profile", EmployerProfileViewSet, basename="employer-profile")
router.register("candidate-profile", CandidateProfileViewSet, basename="candidate-profile")
router.register("listings", OpportunityViewSet, basename="opportunity")
router.register("applications", ApplicationViewSet, basename="opportunity-application")
router.register("talents", TalentViewSet, basename="opportunity-talent")

urlpatterns = router.urls
