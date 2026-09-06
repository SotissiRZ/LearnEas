import test from "node:test";
import assert from "node:assert/strict";
import { readFrontend, readRepo } from "./test-paths.mjs";

const models = readRepo("backend/apps/opportunities/models.py");
const services = readRepo("backend/apps/opportunities/services.py");
const views = readRepo("backend/apps/opportunities/views.py");
const tasks = readRepo("backend/apps/notifications/tasks.py");
const dashboard = readFrontend("app/dashboard/employer/page.tsx");
const company = readFrontend("app/companies/[slug]/page.tsx");

test("v85 matching talent est explicable et rattache a une offre du recruteur", () => {
  assert.match(services, /def match_opportunity_breakdown/);
  assert.match(services, /missing_required_skills/);
  assert.match(views, /match_opportunity_breakdown/);
  assert.match(dashboard, /Pourquoi ce score \?/);
  assert.match(dashboard, /min_match_score/);
});

test("v85 recherches talents sauvegardees sont persistantes et alertables", () => {
  assert.match(models, /class SavedTalentSearch/);
  assert.match(models, /alerts_enabled/);
  assert.match(views, /class SavedTalentSearchViewSet/);
  assert.match(tasks, /def dispatch_saved_talent_search_alerts/);
  assert.match(dashboard, /Recherches sauvegardées/);
});

test("v85 verification entreprise separe approbation profil et identite legale", () => {
  assert.match(models, /class VerificationStatus/);
  assert.match(models, /registration_number/);
  assert.match(views, /def submit_verification/);
  assert.match(views, /def verify_identity/);
  assert.match(company, /company\.is_identity_verified/);
});

test("v85 ATS permet un deplacement drag and drop tout en gardant la validation serveur", () => {
  assert.match(dashboard, /draggable=\{movable\}/);
  assert.match(dashboard, /onDrop=\{\(\) => dropOn\(status\)\}/);
  assert.match(views, /Cette candidature est dans un état final et ne peut plus changer d'étape/);
});

test("v85 justificatifs entreprise restent hors des medias publics", () => {
  const nginx = readRepo("docker/nginx/nginx.conf");
  const admin = readRepo("backend/apps/opportunities/admin.py");
  assert.match(nginx, /\/media\/employers\/verification\//);
  assert.match(admin, /sign_private_media_name/);
  assert.match(admin, /verification_document_secure/);
});

test("v85 alertes recherches sauvegardees utilisent un curseur composite sans perdre de talents", () => {
  assert.match(models, /last_checked_candidate_id/);
  assert.match(tasks, /Q\(updated_at__gt=since\) \| Q\(updated_at=since, id__gt=cursor_id\)/);
  assert.match(tasks, /order_by\("updated_at", "id"\)/);
});
