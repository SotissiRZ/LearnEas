import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";

const root = process.cwd();
const read = (path) => readFileSync(join(root, path), "utf8");

test("CSP principale bloque les scripts inline", () => {
  const middleware = read("middleware.ts");
  const main = middleware.split("const runnerCsp")[0];
  assert.match(main, /script-src 'self' 'nonce-\$\{nonce\}' 'strict-dynamic'/);
  assert.doesNotMatch(main, /script-src[^\n]*unsafe-inline/);
  assert.match(main, /NODE_ENV === \"development\" \? \" 'unsafe-eval'\" : \"\"/);
  assert.doesNotMatch(main, /script-src 'self' 'unsafe-eval'/);
});

test("runner de code est confine et reste embeddable seulement same-origin", () => {
  const live = read("app/live/session/[id]/page.tsx");
  const middleware = read("middleware.ts");
  const nextConfig = read("next.config.js");
  assert.match(live, /src="\/code-runner\/index\.html"/);
  assert.match(live, /sandbox="allow-scripts"/);
  assert.doesNotMatch(live, /sandbox="[^"]*allow-same-origin[^"]*"/);
  assert.doesNotMatch(live, /\(0,eval\)/);
  assert.match(middleware, /X-Frame-Options", "SAMEORIGIN"/);
  assert.match(middleware, /X-Frame-Options", "DENY"/);
  assert.doesNotMatch(nextConfig, /X-Frame-Options/);
});

test("realtime supprime le poll permanent a une seconde", () => {
  const live = read("app/live/session/[id]/page.tsx");
  assert.match(live, /realtime-ticket/);
  assert.match(live, /new WebSocket\(url\)/);
  assert.doesNotMatch(live, /setInterval\(pollSignals,\s*1000\)/);
  assert.match(live, /fallbackTimer = window\.setInterval/);
});

test("aucun JWT persistant dans le stockage navigateur", () => {
  const api = read("lib/api.ts");
  assert.doesNotMatch(api, /localStorage\.setItem\(["']learneas_(access|refresh)/);
  assert.doesNotMatch(api, /sessionStorage\.setItem\(["']learneas_(access|refresh)/);
});
