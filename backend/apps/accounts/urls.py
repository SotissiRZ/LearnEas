from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    LoginView, RegisterView, MeView, InstructorApplyView,
    PasswordResetRequestView, PasswordResetConfirmView,
    AdminUserViewSet, AdminInstructorApplicationViewSet, AdminPlatformSettingsView, PublicPlatformSettingsView,
    InstructorOverviewView, InstructorStudentsView, ChangePasswordView,
)

router = DefaultRouter()
router.register("admin/users", AdminUserViewSet, basename="admin-user")
router.register("admin/instructor-applications", AdminInstructorApplicationViewSet, basename="admin-instructor-application")

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),
    path("me/", MeView.as_view(), name="me"),
    path("become-instructor/", InstructorApplyView.as_view(), name="become-instructor"),
    path("instructor/overview/", InstructorOverviewView.as_view(), name="instructor-overview"),
    path("instructor/students/", InstructorStudentsView.as_view(), name="instructor-students"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("password-reset-confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("platform-settings/", PublicPlatformSettingsView.as_view(), name="platform-settings"),
    path("admin/platform-settings/", AdminPlatformSettingsView.as_view(), name="admin-platform-settings"),
    path("", include(router.urls)),
]
