from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ProjectAssignmentViewSet, ProjectSubmissionViewSet, PortfolioProfileViewSet, PortfolioItemViewSet, public_portfolio

router = DefaultRouter()
router.register("assignments", ProjectAssignmentViewSet, basename="project-assignment")
router.register("submissions", ProjectSubmissionViewSet, basename="project-submission")
router.register("portfolio-profile", PortfolioProfileViewSet, basename="portfolio-profile")
router.register("portfolio-items", PortfolioItemViewSet, basename="portfolio-item")

urlpatterns = [
    path("portfolio/<slug:slug>/", public_portfolio, name="public-portfolio"),
] + router.urls
