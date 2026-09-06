from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import SupportTicket, SupportMessage, ModerationReport, ModerationActionLog

User = get_user_model()


class SupportAndModerationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="student1", email="student1@example.com", password="x", role="student")
        self.other = User.objects.create_user(username="student2", email="student2@example.com", password="x", role="student")
        self.admin = User.objects.create_user(username="admin1", email="admin@example.com", password="x", role="admin")

    def test_ticket_is_private_and_initial_message_is_created(self):
        self.client.force_authenticate(self.user)
        created = self.client.post("/api/support/tickets/", {"subject": "Paiement bloqué", "category": "payment", "initial_message": "Mon paiement reste en attente."}, format="json")
        self.assertEqual(created.status_code, 201)
        ticket = SupportTicket.objects.get(pk=created.data["id"])
        self.assertEqual(ticket.requester, self.user)
        self.assertEqual(ticket.messages.count(), 1)
        self.client.force_authenticate(self.other)
        hidden = self.client.get(f"/api/support/tickets/{ticket.id}/")
        self.assertEqual(hidden.status_code, 404)

    def test_admin_reply_notifies_and_user_can_reply(self):
        ticket = SupportTicket.objects.create(requester=self.user, subject="Besoin aide", category="technical")
        SupportMessage.objects.create(ticket=ticket, author=self.user, body="Le lecteur ne démarre pas.")
        self.client.force_authenticate(self.admin)
        reply = self.client.post(f"/api/support/tickets/{ticket.id}/messages/", {"body": "Pouvez-vous réessayer après actualisation ?"}, format="json")
        self.assertEqual(reply.status_code, 201)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, SupportTicket.Status.WAITING_USER)
        self.assertEqual(ticket.assigned_to, self.admin)
        self.client.force_authenticate(self.user)
        answer = self.client.post(f"/api/support/tickets/{ticket.id}/messages/", {"body": "Oui, le problème persiste."}, format="json")
        self.assertEqual(answer.status_code, 201)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, SupportTicket.Status.IN_PROGRESS)

    def test_reports_are_private_and_only_admin_can_moderate(self):
        self.client.force_authenticate(self.user)
        created = self.client.post("/api/support/reports/", {"target_type": "review", "target_id": "42", "target_label": "Avis #42", "reason": "harassment", "details": "Propos insultants."}, format="json")
        self.assertEqual(created.status_code, 201)
        report_id = created.data["id"]
        denied = self.client.patch(f"/api/support/reports/{report_id}/", {"status": "actioned"}, format="json")
        self.assertEqual(denied.status_code, 403)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(f"/api/support/reports/{report_id}/").status_code, 404)
        self.client.force_authenticate(self.admin)
        updated = self.client.patch(f"/api/support/reports/{report_id}/", {"status": "actioned", "severity": "high", "action_taken": "warning", "resolution_note": "Compte averti."}, format="json")
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(ModerationActionLog.objects.filter(report_id=report_id).count(), 1)

    def test_duplicate_active_report_is_rejected(self):
        ModerationReport.objects.create(reporter=self.user, target_type="comment", target_id="9", reason="spam")
        self.client.force_authenticate(self.user)
        duplicate = self.client.post("/api/support/reports/", {"target_type": "comment", "target_id": "9", "reason": "spam"}, format="json")
        self.assertEqual(duplicate.status_code, 400)
