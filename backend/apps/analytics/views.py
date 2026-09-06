import csv
from django.http import HttpResponse
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.throttles import ProductAnalyticsRateThrottle
from .models import ProductEvent
from .services import analytics_snapshot, hashed_session, sanitize_path, sanitize_properties


class IsAdminRole(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.role == "admin")


class ProductEventView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ProductAnalyticsRateThrottle]

    def post(self, request):
        event_name = str(request.data.get("event_name") or "")[:64]
        allowed = {value for value, _label in ProductEvent.EventName.choices}
        if event_name not in allowed:
            return Response({"event_name": ["Événement analytics inconnu."]}, status=status.HTTP_400_BAD_REQUEST)
        ProductEvent.objects.create(
            event_name=event_name,
            user=request.user if getattr(request.user, "is_authenticated", False) else None,
            session_key=hashed_session(request.data.get("session_id")),
            path=sanitize_path(request.data.get("path")),
            properties=sanitize_properties(request.data.get("properties")),
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminAnalyticsOverviewView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        try:
            days = int(request.query_params.get("period", 30))
        except (TypeError, ValueError):
            days = 30
        return Response(analytics_snapshot(days))


class AdminAnalyticsExportView(APIView):
    permission_classes = [IsAdminRole]

    def get(self, request):
        try:
            days = int(request.query_params.get("period", 30))
        except (TypeError, ValueError):
            days = 30
        data = analytics_snapshot(days)
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="kalanpro-analytics-{data["period_days"]}j.csv"'
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow(["KalanPro Analytics", f'{data["period_days"]} jours'])
        writer.writerow([])
        for section in ("acquisition", "finance", "learning", "recruitment"):
            writer.writerow([section.upper()])
            for key, value in data[section].items():
                writer.writerow([key, value])
            writer.writerow([])
        writer.writerow(["SÉRIE TEMPORELLE"])
        writer.writerow(["date", "registrations", "active_users", "paid_orders", "gmv", "applications"])
        for row in data["timeline"]:
            writer.writerow([row["date"], row["registrations"], row["active_users"], row["paid_orders"], row["gmv"], row["applications"]])
        return response
