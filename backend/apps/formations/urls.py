from rest_framework.routers import DefaultRouter
from .views import InteractiveFormationViewSet, FormationSessionViewSet, MyFormationsViewSet

router = DefaultRouter()
router.register("formations", InteractiveFormationViewSet, basename="formation")
router.register("sessions", FormationSessionViewSet, basename="formation-session")
router.register("my-formations", MyFormationsViewSet, basename="my-formation")

urlpatterns = router.urls
