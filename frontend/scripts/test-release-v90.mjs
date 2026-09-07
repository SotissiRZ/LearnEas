import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { readFrontend, readRepo } from "./test-paths.mjs";

test("v90 fournit un release gate backend sans modifier les migrations métier", () => {
  const command = readRepo("backend/apps/common/management/commands/release_gate.py");
  const release = readRepo("backend/apps/common/release.py");
  assert.match(command, /--strict-infra/);
  assert.match(command, /--deploy/);
  assert.match(release, /pending_migrations/);
  assert.match(release, /REQUIRE_REMOTE_MEDIA/);
});

test("v90 smoke teste frontend backend catalogues sécurité et auth démo optionnelle", () => {
  const smoke = readFrontend("scripts/release-smoke.mjs");
  for (const marker of ["/healthz", "/health/live/", "/health/ready/", "/catalog/courses/", "/catalog/pdfs/", "/opportunities/listings/", "content-security-policy", "--demo-auth", "/ops/health/"]) {
    assert.ok(smoke.includes(marker), `missing ${marker}`);
  }
});

test("v90 charge mesure p95 taux erreur et concurrence sans dépendance externe", () => {
  const load = readFrontend("scripts/release-load.mjs");
  assert.match(load, /RELEASE_LOAD_CONCURRENCY/);
  assert.match(load, /RELEASE_LOAD_MAX_P95_MS/);
  assert.match(load, /RELEASE_LOAD_MAX_ERROR_RATE/);
  assert.doesNotMatch(load, /from\s+["'](axios|autocannon|k6)/);
});

test("v90 chaos injecte latence et 503 avec retry seulement sur GET idempotent", () => {
  const chaos = readFrontend("scripts/release-chaos.mjs");
  assert.match(chaos, /synthetic network fault/);
  assert.match(chaos, /clientTimeoutMs \+ 250/);
  assert.match(chaos, /maxRetries = 2/);
  assert.match(chaos, /resilientGet/);
});

test("v90 branche les gates dans npm et la CI d'intégration Docker", () => {
  const pkg = JSON.parse(readFrontend("package.json"));
  assert.match(pkg.scripts["test:unit"], /test-release-v90\.mjs/);
  assert.equal(pkg.scripts["release:smoke"], "node scripts/release-smoke.mjs");
  assert.equal(pkg.scripts["release:load"], "node scripts/release-load.mjs");
  assert.equal(pkg.scripts["release:chaos"], "node scripts/release-chaos.mjs");
  const ci = readRepo(".github/workflows/ci.yml");
  assert.match(ci, /integration:/);
  assert.match(ci, /release:qualify:dev/);
});
