import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");

test("v79 CI couvre backend frontend migrations et build", () => {
  const ci = read("../.github/workflows/ci.yml");
  assert.match(ci, /python manage\.py makemigrations --check --dry-run/);
  assert.match(ci, /python manage\.py test/);
  assert.match(ci, /python manage\.py check --deploy/);
  assert.match(ci, /npm run test:ci/);
  assert.match(ci, /npm run build:check/);
});

test("v79 separe liveness et readiness et Docker sonde uniquement la liveness", () => {
  const urls = read("../backend/learneas/urls.py");
  const dev = read("../docker-compose.dev.yml");
  const prod = read("../docker-compose.yml");
  assert.match(urls, /api\/health\/live\//);
  assert.match(urls, /api\/health\/ready\//);
  assert.match(dev, /api\/health\/live\//);
  assert.match(prod, /api\/health\/live\//);
  assert.match(dev, /redis-cli["', ]+ping/);
});

test("v79 request-id et logs structures sont configures", () => {
  const settings = read("../backend/learneas/settings.py");
  const middleware = read("../backend/apps/common/middleware.py");
  const logging = read("../backend/apps/common/logging.py");
  assert.match(settings, /apps\.common\.middleware\.request_id_middleware/);
  assert.match(settings, /LOG_FORMAT/);
  assert.match(middleware, /X-Request-ID/);
  assert.match(logging, /JsonFormatter/);
});

test("v79 ignore et nettoie les artefacts Next de validation", () => {
  const ignore = read("../.gitignore");
  const buildCheck = read("scripts/build-check.mjs");
  assert.match(ignore, /frontend\/\.next-build-check\//);
  assert.match(buildCheck, /rm\(path\.join\(root, distDir\)/);
  assert.doesNotMatch(buildCheck, /if \(code === 0\)/);
});

test("v79 commandes de sauvegarde et restauration PostgreSQL sont presentes", () => {
  const backup = read("../backend/apps/common/management/commands/backup_database.py");
  const restore = read("../backend/apps/common/management/commands/restore_database.py");
  const dockerfile = read("../backend/Dockerfile");
  assert.match(backup, /pg_dump/);
  assert.match(restore, /pg_restore/);
  assert.match(restore, /--confirm/);
  assert.match(dockerfile, /postgresql-client/);
});


test("v79 error boundary remonte un signal minimal sans stack", () => {
  const boundary = read("app/error.tsx");
  const backend = read("../backend/apps/common/views.py");
  assert.match(boundary, /telemetry\/client-error/);
  assert.doesNotMatch(boundary, /error\.stack/);
  assert.match(backend, /ClientErrorTelemetryView/);
  assert.match(backend, /Aucun message\/stack/);
});

test("v80 journalise tentatives evenements et anomalies de paiement", () => {
  const models = read("../backend/apps/payments/models.py");
  const lifecycle = read("../backend/apps/payments/lifecycle.py");
  assert.match(models, /class PaymentAttempt/);
  assert.match(models, /class PaymentEvent/);
  assert.match(models, /class PaymentIssue/);
  assert.match(lifecycle, /def redact_payload/);
  assert.match(lifecycle, /uniq_payment_external_event|external_id/);
  assert.match(lifecycle, /AMOUNT_MISMATCH/);
  assert.match(lifecycle, /CURRENCY_MISMATCH/);
});

test("v80 reconcile les paiements sans auto-annuler un wallet stale", () => {
  const tasks = read("../backend/apps/payments/tasks.py");
  const settings = read("../backend/learneas/settings.py");
  assert.match(tasks, /classify_verification/);
  assert.match(tasks, /flag_stale_pending_payments/);
  assert.match(tasks, /PaymentIssue\.IssueType\.STALE_PENDING/);
  assert.doesNotMatch(tasks, /expires_at__lte=now[\s\S]{0,800}status = Order\.Status\.FAILED/);
  assert.match(settings, /payment-stale-review-hourly/);
});

test("v80 admin expose un audit financier par commande", () => {
  const views = read("../backend/apps/payments/views.py");
  const adminPage = read("app/dashboard/admin/page.tsx");
  assert.match(views, /def payment_audit/);
  assert.match(views, /def resolve_payment_issue/);
  assert.match(adminPage, /payment-audit/);
  assert.match(adminPage, /Audit du paiement/);
  assert.match(adminPage, /CinetPay \/ Mobile Money/);
});

test("v80 finance permet filtrage anomalies et export CSV", () => {
  const views = read("../backend/apps/payments/views.py");
  const adminPage = read("app/dashboard/admin/page.tsx");
  assert.match(views, /def export_csv/);
  assert.match(views, /has_payment_issue/);
  assert.match(adminPage, /Anomalies seulement/);
  assert.match(adminPage, /Export CSV/);
});

test("v80 retour Mobile Money limite les appels prestataire", () => {
  const page = read("app/checkout/return/page.tsx");
  assert.match(page, /pollInternalStatus/);
  assert.match(page, /\[3, 7\]\.includes/);
  assert.match(page, /api\.get<ConfirmedOrder>/);
  assert.match(page, /réconciliation automatiquement/);
});

test("v80 ne marque jamais une tentative payee avant validation montant devise", () => {
  const lifecycle = read("../backend/apps/payments/lifecycle.py");
  assert.match(lifecycle, /status = PaymentAttempt\.Status\.CHECKED/);
  assert.match(lifecycle, /return "amount_mismatch"/);
  assert.match(lifecycle, /return "currency_mismatch"/);
  assert.match(lifecycle, /def mark_attempt_paid/);
  assert.doesNotMatch(lifecycle, /status = PaymentAttempt\.Status\.PAID if verification\.get\("paid"\)/);
});

test("v83 cohortes gerent une liste d'attente avec priorite temporaire", () => {
  const cohorts = read("../backend/apps/formations/cohorts.py");
  const models = read("../backend/apps/formations/models.py");
  const access = read("components/formation/FormationAccessCard.tsx");
  assert.match(models, /class FormationWaitlistEntry/);
  assert.match(cohorts, /def refresh_waitlist/);
  assert.match(cohorts, /COHORT_WAITLIST_OFFER_HOURS/);
  assert.match(cohorts, /FormationSeatReservation/);
  assert.match(access, /join_waitlist/);
  assert.match(access, /waitlist_position/);
  assert.match(access, /place vous est réservée temporairement/i);
});

test("v83 packs mentorat sont achetables et consommes transactionnellement", () => {
  const models = read("../backend/apps/formations/models.py");
  const payments = read("../backend/apps/payments/views.py");
  const service = read("../backend/apps/formations/mentorship.py");
  const card = read("components/mentorship/MentorshipBookingCard.tsx");
  assert.match(models, /class MentorshipPack/);
  assert.match(models, /class MentorshipPass/);
  assert.match(payments, /MENTOR_PACK/);
  assert.match(payments, /MentorshipPass\.objects\.get_or_create/);
  assert.match(service, /MentorshipPass\.objects\.select_for_update/);
  assert.match(card, /addMentorshipPack/);
  assert.match(card, /pass_id/);
});

test("v83 mentorat permet reprogrammation et disponibilites recurrentes sans slots fantomes", () => {
  const models = read("../backend/apps/formations/models.py");
  const service = read("../backend/apps/formations/mentorship.py");
  const views = read("../backend/apps/formations/views.py");
  assert.match(models, /class MentorshipAvailabilityRule/);
  assert.match(models, /availability_rule = models\.ForeignKey/);
  assert.match(service, /def reschedule_booking/);
  assert.match(service, /def generate_rule_slots/);
  assert.match(service, /should_be_active/);
  assert.match(views, /Règle désactivée car elle possède déjà un historique/);
});

test("v83 taches periodiques rafraichissent cohortes et disponibilites mentorat", () => {
  const tasks = read("../backend/apps/formations/tasks.py");
  const settings = read("../backend/learneas/settings.py");
  assert.match(tasks, /def refresh_cohort_waitlists/);
  assert.match(tasks, /def generate_recurring_mentorship_slots/);
  assert.match(settings, /cohort-waitlist-refresh/);
  assert.match(settings, /mentorship-recurring-slots/);
});


test("v83 corrige les dependances runtime mentorat et liste formation", () => {
  const mentorship = read("../backend/apps/formations/mentorship.py");
  const serializers = read("../backend/apps/formations/serializers.py");
  assert.match(mentorship, /from django\.contrib\.auth import get_user_model/);
  assert.match(mentorship, /from zoneinfo import ZoneInfo, ZoneInfoNotFoundError/);
  assert.match(serializers, /from django\.utils import timezone/);
});

test("v83 Docker dev execute aussi la file media et expose le TTL waitlist", () => {
  const dev = read("../docker-compose.dev.yml");
  const prod = read("../docker-compose.yml");
  assert.match(dev, /celery_media_worker:/);
  assert.match(dev, /-Q", "media"/);
  assert.match(dev, /COHORT_WAITLIST_OFFER_HOURS/);
  assert.match(prod, /COHORT_WAITLIST_OFFER_HOURS/);
});

test("v83 settings offline ne dependent pas d'un os global non importe", () => {
  const settings = read("../backend/learneas/settings.py");
  assert.match(settings, /OFFLINE_VIDEO_ENABLED = config\(/);
  assert.match(settings, /OFFLINE_VIDEO_MAX_HEIGHT = config\(/);
  assert.match(settings, /OFFLINE_VIDEO_MAX_MB = config\(/);
  assert.match(settings, /OFFLINE_PROGRESS_TOKEN_MAX_AGE = config\(/);
  assert.doesNotMatch(settings, /OFFLINE_VIDEO_ENABLED = os\.getenv/);
});


test("v84 portfolio expose preuves riches et certificats explicitement selectionnes", () => {
  const models = read("../backend/apps/projects/models.py");
  const serializers = read("../backend/apps/projects/serializers.py");
  const editor = read("app/dashboard/student/portfolio/page.tsx");
  const publicPage = read("app/portfolio/[slug]/page.tsx");
  assert.match(models, /class PortfolioCertificate/);
  assert.match(models, /role = models\.CharField/);
  assert.match(models, /outcome = models\.TextField/);
  assert.match(models, /stack = models\.JSONField/);
  assert.match(serializers, /selected_certificate_ids/);
  assert.match(serializers, /show_contact_email/);
  assert.match(editor, /Certificats publics/);
  assert.match(editor, /Résultat \/ impact/);
  assert.match(publicPage, /Certificats vérifiables/);
  assert.match(publicPage, /Démo vidéo/);
});

test("v84 certificats fournissent PDF officiel et entree CV structuree", () => {
  const views = read("../backend/apps/enrollments/views.py");
  const serializers = read("../backend/apps/enrollments/serializers.py");
  const card = read("components/ui/CertificateCard.tsx");
  assert.match(views, /class CertificatePDFView/);
  assert.match(views, /application\/pdf/);
  assert.match(views, /reportlab\.pdfgen/);
  assert.match(serializers, /pdf_url/);
  assert.match(serializers, /cv_entry/);
  assert.match(card, /Télécharger PDF/);
  assert.match(card, /Copier pour mon CV/);
});

test("v84 preserve la preuve verifiee tout en autorisant la presentation riche", () => {
  const views = read("../backend/apps/projects/views.py");
  assert.match(views, /instance\.is_verified/);
  assert.match(views, /"problem", "objective", "outcome", "stack", "video_url"/);
  assert.match(views, /Les informations vérifiées d'un projet KalanPro ne peuvent pas être altérées/);
});
