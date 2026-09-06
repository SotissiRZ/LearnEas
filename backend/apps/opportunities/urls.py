from rest_framework.routers import DefaultRouter
from .views import (
    EmployerProfileViewSet, EmployerDirectoryViewSet, CandidateProfileViewSet,
    OpportunityViewSet, ApplicationViewSet, TalentViewSet, TalentBookmarkViewSet, SavedTalentSearchViewSet,
)

router = DefaultRouter()
router.register("employer-profile", EmployerProfileViewSet, basename="employer-profile")
router.register("companies", EmployerDirectoryViewSet, basename="employer-company")
router.register("candidate-profile", CandidateProfileViewSet, basename="candidate-profile")
router.register("listings", OpportunityViewSet, basename="opportunity")
router.register("applications", ApplicationViewSet, basename="opportunity-application")
router.register("talents", TalentViewSet, basename="opportunity-talent")
router.register("talent-bookmarks", TalentBookmarkViewSet, basename="talent-bookmark")
router.register("saved-talent-searches", SavedTalentSearchViewSet, basename="saved-talent-search")

urlpatterns = router.urls
