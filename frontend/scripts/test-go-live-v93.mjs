import test from "node:test";
import assert from "node:assert/strict";
import { readFrontend, readRepo } from "./test-paths.mjs";

const dockerfile = readRepo("backend/Dockerfile");
const startWeb = readRepo("backend/docker/start-web.sh");
const entrypoint = readRepo("backend/docker/entrypoint.sh");
const production = readRepo("backend/apps/common/production.py");
const preflight = readRepo("backend/apps/common/management/commands/production_preflight.py");
const release = readRepo("backend/apps/common/release.py");
const backup = readRepo("backend/apps/common/management/commands/backup_database.py");
const restore = readRepo("backend/apps/common/management/commands/restore_database.py");
const envCheck = readFrontend("scripts/production-env-check.mjs");
const prodSmoke = readFrontend("scripts/postdeploy-smoke.mjs");
const nextConfig = readFrontend("next.config.js");
const docs = readRepo("docs/V93_GO_LIVE.md");

test("v93 backend écoute le PORT de la plateforme sans casser Docker local", () => {
  assert.match(dockerfile, /start-web\.sh/);
  assert.match(startWeb, /PORT:-8000/);
  assert.match(startWeb, /exec daphne/);
  assert.match(entrypoint, /RUN_MIGRATIONS_ON_BOOT/);
  assert.match(entrypoint, /COLLECTSTATIC_ON_BOOT/);
});

test("v93 fournit un contrat production bloquant mais sans appel fournisseur", () => {
  for (const marker of ["payment_provider_missing", "transactional_email_not_ready", "turn_not_ready", "remote_media_incomplete", "malware_scan_incomplete"]) {
    assert.ok(production.includes(marker), `missing ${marker}`);
  }
  assert.match(preflight, /--fail-on-warnings/);
  assert.match(release, /build_production_preflight_snapshot/);
  assert.match(release, /production:/);
});

test("v93 frontend valide le proxy Vercel et interdit les secrets NEXT_PUBLIC", () => {
  assert.match(envCheck, /API_PROXY_TARGET/);
  assert.match(envCheck, /NEXT_PUBLIC_API_URL/);
  assert.match(envCheck, /NEXT_PUBLIC_WS_URL/);
  assert.match(envCheck, /public_secret_like_variable/);
  assert.match(nextConfig, /poweredByHeader: false/);
});

test("v93 smoke production teste HTTPS proxy readiness CORS et CSP", () => {
  for (const marker of ["RELEASE_BASE_URL", "RELEASE_BACKEND_URL", "/api/health/ready/", "access-control-allow-origin", "content-security-policy"]) {
    assert.ok(prodSmoke.includes(marker), `missing ${marker}`);
  }
});

test("v93 sauvegarde et restauration peuvent utiliser le stockage privé", () => {
  assert.match(backup, /--upload/);
  assert.match(backup, /backups\/database\//);
  assert.match(restore, /--storage-key/);
  assert.match(restore, /default_storage\.open/);
});

test("v93 documente Railway Vercel webhooks et rollback", () => {
  for (const marker of ["Railway", "Vercel", "stripe/webhook", "whatsapp/webhook", "release:smoke:prod", "Rollback"]) {
    assert.ok(docs.includes(marker), `missing ${marker}`);
  }
});
