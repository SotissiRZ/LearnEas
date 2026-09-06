from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.accounts.models import User
from apps.notifications.models import InAppNotification
from apps.notifications.services import queue_in_app_event
from .models import SupportTicket, SupportMessage, ModerationReport, ModerationActionLog
from .serializers import (
    SupportTicketSerializer, SupportMessageSerializer,
    ModerationReportSerializer, ModerationReportAdminSerializer,
)


def _is_admin(user):
    return bool(user and user.is_authenticated and user.role == User.Role.ADMIN)


def _notify_admins(*, event_key, title, body, action_url, metadata=None, priority=InAppNotification.Priority.NORMAL):
    for admin in User.objects.filter(role=User.Role.ADMIN, is_active=True).only("id"):
        queue_in_app_event(
            user=admin,
            event_key=f"{event_key}:admin:{admin.id}",
            category=InAppNotification.Category.SYSTEM,
            event_type="support_admin",
            title=title,
            body=body,
            action_url=action_url,
            metadata=metadata or {},
            priority=priority,
        )


class SupportTicketViewSet(viewsets.ModelViewSet):
    serializer_class = SupportTicketSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "category", "priority", "assigned_to"]
    search_fields = ["reference", "subject", "requester__email", "requester__first_name", "requester__last_name"]
    ordering_fields = ["created_at", "updated_at", "last_message_at", "priority", "status"]
    ordering = ["-last_message_at", "-created_at"]

    def get_queryset(self):
        qs = SupportTicket.objects.select_related("requester", "assigned_to").annotate(message_count=Count("messages"))
        if _is_admin(self.request.user):
            return qs
        return qs.filter(requester=self.request.user)

    def perform_create(self, serializer):
        ticket = serializer.save()
        _notify_admins(
            event_key=f"support-ticket:{ticket.id}:created",
            title=f"Nouveau ticket {ticket.reference}",
            body=f"{ticket.requester.email} · {ticket.subject}",
            action_url="/dashboard/admin?tab=moderation",
            metadata={"ticket_id": ticket.id, "reference": ticket.reference},
            priority=InAppNotification.Priority.HIGH if ticket.priority == SupportTicket.Priority.HIGH else InAppNotification.Priority.NORMAL,
        )

    def update(self, request, *args, **kwargs):
        if not _is_admin(request.user):
            return Response({"detail": "Seul le support peut modifier le traitement d'un ticket."}, status=403)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not _is_admin(request.user):
            return Response({"detail": "Seul le support peut modifier le traitement d'un ticket."}, status=403)
        ticket = self.get_object()
        response = super().partial_update(request, *args, **kwargs)
        ticket.refresh_from_db()
        changed = []
        now = timezone.now()
        if ticket.status == SupportTicket.Status.RESOLVED and ticket.resolved_at is None:
            ticket.resolved_at = now; changed.append("resolved_at")
        elif ticket.status != SupportTicket.Status.RESOLVED and ticket.resolved_at is not None:
            ticket.resolved_at = None; changed.append("resolved_at")
        if ticket.status == SupportTicket.Status.CLOSED and ticket.closed_at is None:
            ticket.closed_at = now; changed.append("closed_at")
        elif ticket.status != SupportTicket.Status.CLOSED and ticket.closed_at is not None:
            ticket.closed_at = None; changed.append("closed_at")
        if changed:
            ticket.save(update_fields=changed + ["updated_at"])
        queue_in_app_event(
            user=ticket.requester,
            event_key=f"support-ticket:{ticket.id}:status:{ticket.status}:{int(ticket.updated_at.timestamp())}",
            category=InAppNotification.Category.SYSTEM,
            event_type="support_status",
            title=f"Ticket {ticket.reference} · {ticket.get_status_display()}",
            body=ticket.subject,
            action_url=f"/support?ticket={ticket.id}",
            metadata={"ticket_id": ticket.id, "status": ticket.status},
        )
        return Response(self.get_serializer(ticket).data)

    @action(detail=True, methods=["get", "post"], url_path="messages")
    def messages(self, request, pk=None):
        ticket = self.get_object()
        if request.method == "GET":
            rows = ticket.messages.select_related("author").all()
            return Response(SupportMessageSerializer(rows, many=True).data)
        if ticket.status == SupportTicket.Status.CLOSED:
            return Response({"detail": "Ce ticket est fermé. Ouvrez un nouveau ticket si nécessaire."}, status=409)
        body = str(request.data.get("body", "") or "").strip()
        if not body:
            return Response({"body": ["Le message ne peut pas être vide."]}, status=400)
        if len(body) > 6000:
            return Response({"body": ["Le message est limité à 6 000 caractères."]}, status=400)
        admin_reply = _is_admin(request.user)
        with transaction.atomic():
            message = SupportMessage.objects.create(ticket=ticket, author=request.user, body=body, is_staff_reply=admin_reply)
            ticket.last_message_at = message.created_at or timezone.now()
            if admin_reply:
                ticket.status = SupportTicket.Status.WAITING_USER
                if not ticket.assigned_to_id:
                    ticket.assigned_to = request.user
            else:
                ticket.status = SupportTicket.Status.IN_PROGRESS
                ticket.resolved_at = None
            ticket.closed_at = None
            ticket.save(update_fields=["last_message_at", "status", "assigned_to", "resolved_at", "closed_at", "updated_at"])
        if admin_reply:
            queue_in_app_event(
                user=ticket.requester,
                event_key=f"support-ticket:{ticket.id}:message:{message.id}",
                category=InAppNotification.Category.SYSTEM,
                event_type="support_reply",
                title=f"Réponse du support · {ticket.reference}",
                body=body[:500],
                action_url=f"/support?ticket={ticket.id}",
                metadata={"ticket_id": ticket.id, "message_id": message.id},
                priority=InAppNotification.Priority.HIGH,
            )
        elif ticket.assigned_to_id:
            queue_in_app_event(
                user=ticket.assigned_to,
                event_key=f"support-ticket:{ticket.id}:user-message:{message.id}",
                category=InAppNotification.Category.SYSTEM,
                event_type="support_user_reply",
                title=f"Réponse utilisateur · {ticket.reference}",
                body=body[:500],
                action_url="/dashboard/admin?tab=moderation",
                metadata={"ticket_id": ticket.id, "message_id": message.id},
            )
        return Response(SupportMessageSerializer(message).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="close")
    def close(self, request, pk=None):
        ticket = self.get_object()
        if not (_is_admin(request.user) or ticket.requester_id == request.user.id):
            return Response({"detail": "Action non autorisée."}, status=403)
        if ticket.status != SupportTicket.Status.CLOSED:
            ticket.status = SupportTicket.Status.CLOSED
            ticket.closed_at = timezone.now()
            ticket.save(update_fields=["status", "closed_at", "updated_at"])
        return Response(self.get_serializer(ticket).data)

    @action(detail=False, methods=["get"], url_path="admin-summary")
    def admin_summary(self, request):
        if not _is_admin(request.user):
            return Response({"detail": "Administration requise."}, status=403)
        ticket_counts = {row["status"]: row["count"] for row in SupportTicket.objects.values("status").annotate(count=Count("id"))}
        report_counts = {row["status"]: row["count"] for row in ModerationReport.objects.values("status").annotate(count=Count("id"))}
        return Response({
            "tickets": ticket_counts,
            "reports": report_counts,
            "open_tickets": SupportTicket.objects.exclude(status__in=[SupportTicket.Status.RESOLVED, SupportTicket.Status.CLOSED]).count(),
            "pending_reports": ModerationReport.objects.filter(status__in=[ModerationReport.Status.PENDING, ModerationReport.Status.REVIEWING]).count(),
        })


class ModerationReportViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["status", "severity", "reason", "target_type", "assigned_to"]
    search_fields = ["target_label", "target_id", "details", "reporter__email", "resolution_note"]
    ordering_fields = ["created_at", "updated_at", "severity", "status"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        return ModerationReportAdminSerializer if _is_admin(self.request.user) else ModerationReportSerializer

    def get_queryset(self):
        qs = ModerationReport.objects.select_related("reporter", "assigned_to").prefetch_related("action_logs__moderator")
        if _is_admin(self.request.user):
            return qs
        return qs.filter(reporter=self.request.user)

    def perform_create(self, serializer):
        report = serializer.save()
        _notify_admins(
            event_key=f"moderation-report:{report.id}:created",
            title="Nouveau signalement à examiner",
            body=f"{report.get_reason_display()} · {report.target_label or report.get_target_type_display()}",
            action_url="/dashboard/admin?tab=moderation",
            metadata={"report_id": report.id, "target_type": report.target_type, "target_id": report.target_id},
            priority=InAppNotification.Priority.HIGH,
        )

    def update(self, request, *args, **kwargs):
        if not _is_admin(request.user):
            return Response({"detail": "Seule la modération peut modifier un signalement."}, status=403)
        return self._admin_update(request, partial=False, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if not _is_admin(request.user):
            return Response({"detail": "Seule la modération peut modifier un signalement."}, status=403)
        return self._admin_update(request, partial=True, *args, **kwargs)

    def _admin_update(self, request, partial, *args, **kwargs):
        instance = self.get_object()
        previous_status = instance.status
        previous_action = instance.action_taken
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            report = serializer.save()
            terminal = report.status in [ModerationReport.Status.ACTIONED, ModerationReport.Status.DISMISSED]
            report.resolved_at = timezone.now() if terminal else None
            report.save(update_fields=["resolved_at", "updated_at"])
            if report.status != previous_status or report.action_taken != previous_action or str(request.data.get("resolution_note", "")).strip():
                ModerationActionLog.objects.create(
                    report=report,
                    moderator=request.user,
                    previous_status=previous_status,
                    new_status=report.status,
                    action=report.action_taken,
                    note=report.resolution_note,
                )
        if report.reporter_id:
            queue_in_app_event(
                user=report.reporter,
                event_key=f"moderation-report:{report.id}:status:{report.status}:{report.action_logs.count()}",
                category=InAppNotification.Category.SYSTEM,
                event_type="moderation_status",
                title="Mise à jour de votre signalement",
                body=f"Statut : {report.get_status_display()}.",
                action_url="/support?view=reports",
                metadata={"report_id": report.id, "status": report.status},
            )
        return Response(self.get_serializer(report).data)

    def destroy(self, request, *args, **kwargs):
        if not _is_admin(request.user):
            return Response({"detail": "Seule la modération peut supprimer un signalement."}, status=403)
        return super().destroy(request, *args, **kwargs)
