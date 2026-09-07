import test from "node:test";
import assert from "node:assert/strict";
import { readFrontend, readRepo } from "./test-paths.mjs";

const settings = readRepo("backend/learneas/settings.py");
const storage = readRepo("backend/apps/common/storage.py");
const operations = readRepo("backend/apps/common/operations.py");
const tasks = readRepo("backend/apps/common/tasks.py");
const urls = readRepo("backend/apps/common/urls.py");
const command = readRepo("backend/apps/common/management/commands/migrate_local_media_to_storage.py");
const adminPage = readFrontend("app/dashboard/admin/page.tsx");
const sidebar = readFrontend("components/admin/AdminSidebar.tsx");
const commonViews = readRepo("backend/apps/common/views.py");
const composeDev = readRepo("docker-compose.dev.yml");
const composeProd = readRepo("docker-compose.yml");

test("v89 sépare cache public CDN et médias privés sur S3/R2", () => {
  assert.match(settings, /PUBLIC_MEDIA_BASE_URL/);
  assert.match(settings, /MEDIA_PUBLIC_PREFIXES/);
  assert.match(settings, /KalanProS3Storage/);
  assert.match(storage, /class KalanProS3Storage/);
  assert.match(storage, /public, max-age=.*immutable/);
  assert.match(storage, /private, no-store/);
  assert.match(storage, /is_public_name/);
  assert.match(storage, /generate_presigned_url/);
  assert.match(storage, /PUBLIC_MEDIA_BASE_URL/);
  assert.match(composeDev, /PUBLIC_MEDIA_BASE_URL/);
  assert.match(composeProd, /PUBLIC_MEDIA_BASE_URL/);
});

test("v89 dashboard opérations reste admin-only et sans secrets", () => {
  assert.match(commonViews, /class AdminOperationsView/);
  assert.match(commonViews, /permission_classes = \[IsAdminRole\]/);
  assert.match(urls, /ops\/health/);
  assert.match(operations, /"database"/);
  assert.match(operations, /"broker"/);
  assert.match(operations, /"storage"/);
  assert.match(operations, /"streaming"/);
  assert.doesNotMatch(operations, /AWS_SECRET_ACCESS_KEY|WHATSAPP_ACCESS_TOKEN|AI_API_KEY\s*:/);
  assert.match(sidebar, /Santé plateforme/);
  assert.match(adminPage, /function OperationsTab/);
  assert.match(adminPage, /Analyser stockage/);
});

test("v89 nettoie les multipart abandonnés avec une tâche bornée", () => {
  assert.match(tasks, /cleanup_stale_multipart_uploads/);
  assert.match(tasks, /MULTIPART_UPLOAD_MAX_AGE_HOURS/);
  assert.match(tasks, /MULTIPART_CLEANUP_MAX_ABORTS/);
  assert.match(tasks, /abort_multipart_upload/);
  assert.match(settings, /media-stale-multipart-cleanup-every-6-hours/);
});

test("v89 fournit une migration média locale vers stockage distant non destructive", () => {
  assert.match(command, /--apply/);
  assert.match(command, /USE_S3=True est requis/);
  assert.match(command, /default_storage\.exists/);
  assert.match(command, /default_storage\.save/);
  assert.doesNotMatch(command, /unlink\(|rmtree\(|delete\(/);
});

test("v89 évite le HEAD S3 préalable et signe les segments HLS avec cache contrôlé", () => {
  assert.doesNotMatch(commonViews, /if getattr\(settings, "USE_S3", False\):\s*\n\s*if not default_storage\.exists\(name\)/);
  assert.match(commonViews, /ResponseCacheControl/);
  assert.match(commonViews, /HLS_SEGMENT_CACHE_SECONDS/);
});
