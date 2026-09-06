# Generated for KalanPro V88 support + moderation
import django.db.models.deletion
import apps.support.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="SupportTicket",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reference", models.CharField(default=apps.support.models.ticket_reference, editable=False, max_length=20, unique=True)),
                ("subject", models.CharField(max_length=180)),
                ("category", models.CharField(choices=[("account","Compte et connexion"),("payment","Paiement et remboursement"),("learning","Cours et apprentissage"),("technical","Problème technique"),("recruitment","Emploi et recrutement"),("safety","Sécurité et modération"),("other","Autre")], db_index=True, default="other", max_length=24)),
                ("priority", models.CharField(choices=[("low","Faible"),("normal","Normale"),("high","Haute"),("urgent","Urgente")], db_index=True, default="normal", max_length=12)),
                ("status", models.CharField(choices=[("open","Ouvert"),("in_progress","En cours"),("waiting_user","En attente utilisateur"),("resolved","Résolu"),("closed","Fermé")], db_index=True, default="open", max_length=20)),
                ("last_message_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("closed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assigned_to", models.ForeignKey(blank=True, limit_choices_to={"role":"admin"}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_support_tickets", to=settings.AUTH_USER_MODEL)),
                ("requester", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="support_tickets", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering":["-last_message_at","-created_at","-id"]},
        ),
        migrations.CreateModel(
            name="SupportMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("body", models.TextField()),
                ("is_staff_reply", models.BooleanField(db_index=True, default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("author", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="support_messages", to=settings.AUTH_USER_MODEL)),
                ("ticket", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="support.supportticket")),
            ],
            options={"ordering":["created_at","id"]},
        ),
        migrations.CreateModel(
            name="ModerationReport",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("target_type", models.CharField(choices=[("user","Utilisateur"),("review","Avis"),("comment","Commentaire"),("course","Cours"),("pdf","PDF"),("formation","Formation"),("opportunity","Opportunité"),("message","Message"),("other","Autre")], db_index=True, max_length=24)),
                ("target_id", models.CharField(blank=True, db_index=True, max_length=120)),
                ("target_label", models.CharField(blank=True, max_length=255)),
                ("target_url", models.CharField(blank=True, max_length=500)),
                ("reason", models.CharField(choices=[("harassment","Harcèlement ou menace"),("spam","Spam"),("fraud","Fraude ou arnaque"),("impersonation","Usurpation d'identité"),("inappropriate","Contenu inapproprié"),("illegal","Contenu potentiellement illégal"),("copyright","Droits d'auteur"),("misinformation","Information trompeuse"),("other","Autre")], db_index=True, max_length=24)),
                ("details", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("pending","À examiner"),("reviewing","En cours d'examen"),("actioned","Action effectuée"),("dismissed","Classé sans suite")], db_index=True, default="pending", max_length=16)),
                ("severity", models.CharField(choices=[("low","Faible"),("medium","Moyenne"),("high","Élevée"),("critical","Critique")], db_index=True, default="medium", max_length=12)),
                ("action_taken", models.CharField(choices=[("none","Aucune"),("warning","Avertissement"),("content_removed","Contenu retiré"),("user_restricted","Utilisateur restreint"),("escalated","Escalade")], default="none", max_length=24)),
                ("resolution_note", models.TextField(blank=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("assigned_to", models.ForeignKey(blank=True, limit_choices_to={"role":"admin"}, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_moderation_reports", to=settings.AUTH_USER_MODEL)),
                ("reporter", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="moderation_reports", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering":["-created_at","-id"]},
        ),
        migrations.CreateModel(
            name="ModerationActionLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("previous_status", models.CharField(blank=True, max_length=16)),
                ("new_status", models.CharField(blank=True, max_length=16)),
                ("action", models.CharField(choices=[("none","Aucune"),("warning","Avertissement"),("content_removed","Contenu retiré"),("user_restricted","Utilisateur restreint"),("escalated","Escalade")], default="none", max_length=24)),
                ("note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("moderator", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="moderation_actions", to=settings.AUTH_USER_MODEL)),
                ("report", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="action_logs", to="support.moderationreport")),
            ],
            options={"ordering":["-created_at","-id"]},
        ),
        migrations.AddIndex(model_name="supportticket", index=models.Index(fields=["requester","status","-updated_at"], name="support_ticket_user_status_idx")),
        migrations.AddIndex(model_name="supportticket", index=models.Index(fields=["status","priority","-updated_at"], name="support_ticket_queue_idx")),
        migrations.AddIndex(model_name="supportmessage", index=models.Index(fields=["ticket","created_at"], name="support_message_ticket_idx")),
        migrations.AddIndex(model_name="moderationreport", index=models.Index(fields=["status","severity","-created_at"], name="moderation_queue_idx")),
        migrations.AddIndex(model_name="moderationreport", index=models.Index(fields=["target_type","target_id"], name="moderation_target_idx")),
    ]
