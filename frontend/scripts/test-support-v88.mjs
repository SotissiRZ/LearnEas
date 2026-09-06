import test from "node:test";
import assert from "node:assert/strict";
import { readFrontend, readRepo } from "./test-paths.mjs";

const models = readRepo("backend/apps/support/models.py");
const serializers = readRepo("backend/apps/support/serializers.py");
const views = readRepo("backend/apps/support/views.py");
const urls = readRepo("backend/apps/support/urls.py");
const settings = readRepo("backend/learneas/settings.py");
const rootUrls = readRepo("backend/learneas/urls.py");
const migration = readRepo("backend/apps/support/migrations/0001_support_moderation.py");
const userPage = readFrontend("app/support/page.tsx");
const adminPanel = readFrontend("components/admin/SupportModerationPanel.tsx");
const adminPage = readFrontend("app/dashboard/admin/page.tsx");
const contact = readFrontend("app/contact/page.tsx");
const nav = readFrontend("components/dashboard/DashboardNav.tsx");
const course = readFrontend("app/courses/[slug]/page.tsx");
const pdf = readFrontend("app/pdfs/[slug]/page.tsx");

test("v88 ajoute tickets support prives et conversation suivie", () => {
  assert.match(models, /class SupportTicket/);
  assert.match(models, /class SupportMessage/);
  assert.match(views, /return qs\.filter\(requester=self\.request\.user\)/);
  assert.match(views, /url_path="messages"/);
  assert.match(views, /SupportTicket\.Status\.WAITING_USER/);
  assert.match(views, /SupportTicket\.Status\.IN_PROGRESS/);
  assert.match(serializers, /validated_data\["status"\] = SupportTicket\.Status\.OPEN/);
});

test("v88 signalements sont cloisonnes et moderation admin journalisee", () => {
  assert.match(models, /class ModerationReport/);
  assert.match(models, /class ModerationActionLog/);
  assert.match(views, /return qs\.filter\(reporter=self\.request\.user\)/);
  assert.match(views, /if not _is_admin\(request\.user\)/);
  assert.match(views, /ModerationActionLog\.objects\.create/);
  assert.match(serializers, /Un signalement actif existe déjà/);
  assert.match(serializers, /URL relative KalanPro ou une URL http\(s\)/);
});

test("v88 notifie les reponses support et changements de moderation", () => {
  assert.match(views, /event_type="support_reply"/);
  assert.match(views, /event_type="support_status"/);
  assert.match(views, /event_type="moderation_status"/);
  assert.match(views, /_notify_admins/);
});

test("v88 expose centre support aux trois roles et vrais tickets depuis contact", () => {
  assert.match(userPage, /Centre d’aide KalanPro/);
  assert.match(userPage, /\/support\/tickets\//);
  assert.match(userPage, /\/support\/reports\//);
  assert.match(nav, /href: "\/support"/);
  assert.match(contact, /Ouvrir le centre de support/);
  assert.doesNotMatch(contact, /setSent\(true\)/);
});

test("v88 backoffice combine support signalements et moderation existante", () => {
  assert.match(adminPanel, /Tickets à traiter/);
  assert.match(adminPanel, /Signalements actifs/);
  assert.match(adminPanel, /admin-summary/);
  assert.match(adminPage, /<SupportModerationPanel \/>/);
  assert.match(adminPage, /<ModerationTab/);
});

test("v88 permet signaler les contenus catalogue sans masquer les fonctions existantes", () => {
  assert.match(course, /ReportLink targetType="course"/);
  assert.match(pdf, /ReportLink targetType="pdf"/);
  assert.match(course, /CoursePurchaseCard/);
  assert.match(pdf, /PdfAccessCard/);
});

test("v88 branche app urls et migration additive", () => {
  assert.match(settings, /"apps\.support"/);
  assert.match(rootUrls, /path\("api\/support\/", include\("apps\.support\.urls"\)\)/);
  assert.match(urls, /router\.register\("tickets"/);
  assert.match(urls, /router\.register\("reports"/);
  assert.match(migration, /CreateModel/);
  assert.doesNotMatch(migration, /DeleteModel|RemoveField/);
});
