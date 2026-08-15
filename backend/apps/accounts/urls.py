from django.urls import path
from .views import LoginView, RegisterView, MeView, InstructorApplyView

urlpatterns = [
    path("login/", LoginView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),
    path("me/", MeView.as_view(), name="me"),
    path("become-instructor/", InstructorApplyView.as_view(), name="become-instructor"),
]
