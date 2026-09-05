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

test("v79 separe liveness et readiness et Docker sonde readiness", () => {
  const urls = read("../backend/learneas/urls.py");
  const dev = read("../docker-compose.dev.yml");
  const prod = read("../docker-compose.yml");
  assert.match(urls, /api\/health\/live\//);
  assert.match(urls, /api\/health\/ready\//);
  assert.match(dev, /api\/health\/ready\//);
  assert.match(prod, /api\/health\/ready\//);
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
