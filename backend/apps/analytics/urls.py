from django.urls import path
from .views import ProductEventView, AdminAnalyticsOverviewView, AdminAnalyticsExportView

urlpatterns = [
    path("events/", ProductEventView.as_view(), name="analytics-events"),
    path("admin/overview/", AdminAnalyticsOverviewView.as_view(), name="analytics-admin-overview"),
    path("admin/export/", AdminAnalyticsExportView.as_view(), name="analytics-admin-export"),
]
