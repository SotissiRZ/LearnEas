import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const read = (file) => fs.readFileSync(path.join(root, file), "utf8");

test("assistant IA lourd charge uniquement a la demande", () => {
  const layout = read("app/layout.tsx");
  const lazy = read("components/ai/LazyKalanProAssistant.tsx");
  assert.match(layout, /LazyKalanProAssistant/);
  assert.doesNotMatch(layout, /from "@\/components\/ai\/KalanProAssistant"/);
  assert.match(lazy, /dynamic\(\(\) => import\("@\/components\/ai\/KalanProAssistant"\)/);
  assert.match(lazy, /if \(activated\) return <Assistant initialOpen \/>/);
});

test("restauration auth se fait en un seul refresh reseau", () => {
  const auth = read("hooks/useAuth.ts");
  const backend = read("../backend/apps/accounts/views.py");
  assert.match(auth, /restoreAccessToken<AuthUser>\(\)/);
  const hydrateBlock = auth.slice(auth.indexOf("hydrate: async"), auth.indexOf("login: async"));
  assert.doesNotMatch(hydrateBlock, /api\.get<AuthUser>\("\/auth\/me\/"\)/);
  assert.match(backend, /data\["user"\] = UserSerializer\(user\)\.data/);
});

test("requêtes API interactives ont timeout et deduplication GET", () => {
  const api = read("lib/api.ts");
  assert.match(api, /API_TIMEOUT_MS/);
  assert.match(api, /fetchWithTimeout/);
  assert.match(api, /inFlightGets/);
  assert.match(api, /get: <T>\(path: string\) => dedupedGet<T>\(path\)/);
});

test("docker dev utilise API same-origin", () => {
  const compose = read("../docker-compose.dev.yml");
  assert.match(compose, /NEXT_PUBLIC_API_URL: \/api/);
  assert.match(compose, /API_PROXY_TARGET: http:\/\/backend:8000/);
});


test("proxy dev preserve le slash final exige par Django pour les POST", () => {
  const nextConfig = read("next.config.js");
  assert.match(nextConfig, /destination: `\$\{apiProxyTarget\}\/api\/:path\*\/`/);
  assert.doesNotMatch(nextConfig, /destination: `\$\{apiProxyTarget\}\/api\/:path\*` \}/);

  const login = read("app/login/page.tsx");
  assert.match(login, /err\.message === "Identifiants invalides ou session expirée\."/);
  assert.match(login, /: err\.message/);
});


test("workflow candidat ne charge pas entretiens et offre pour chaque candidature", () => {
  const page = read("app/dashboard/student/opportunities/page.tsx");
  assert.match(page, /const needsInterviews = \["interview", "offer", "hired", "rejected"\]/);
  assert.match(page, /const needsOffer = \["offer", "hired", "rejected"\]/);
  assert.match(page, /Promise\.resolve\(\[\] as RecruitmentInterview\[\]\)/);
});
