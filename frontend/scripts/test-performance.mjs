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

test("docker dev isole les artefacts Next du build de validation", () => {
  const compose = read("../docker-compose.dev.yml");
  const pkg = JSON.parse(read("package.json"));
  const nextConfig = read("next.config.js");
  const buildCheck = read("scripts/build-check.mjs");
  assert.match(compose, /frontend_next_dev:\/app\/.next|frontend_next_dev:\s*\/app\/.next/);
  assert.equal(pkg.scripts["build:check"], "node scripts/build-check.mjs");
  assert.match(nextConfig, /process\.env\.NEXT_DIST_DIR/);
  assert.match(buildCheck, /\.next-build-check/);
  assert.match(buildCheck, /NEXT_DIST_DIR: distDir/);
});

test("cartes catalogue recadrent les apercus et la fiche opportunite affiche le visuel complet", () => {
  const opportunity = read("components/opportunities/OpportunityCard.tsx");
  const opportunityDetail = read("app/opportunities/[slug]/page.tsx");
  const course = read("components/course/CourseCard.tsx");
  const formation = read("components/formation/FormationCard.tsx");
  const pdf = read("components/pdf/PdfCard.tsx");
  const css = read("app/globals.css");
  assert.match(css, /\.catalog-card\s*\{[^}]*max-width:\s*20rem/);
  assert.match(opportunity, /aspect-\[16\/10\]/);
  assert.match(opportunity, /object-cover/);
  assert.match(opportunity, /Voir le visuel complet/);
  assert.match(course, /aspect-\[16\/10\]/);
  assert.match(course, /object-cover/);
  assert.match(formation, /aspect-\[16\/10\]/);
  assert.match(formation, /object-cover/);
  assert.match(pdf, /aspect-\[4\/3\]/);
  assert.match(pdf, /object-cover/);
  assert.match(opportunityDetail, /max-h-\[78vh\]/);
  assert.match(opportunityDetail, /object-contain/);
  assert.match(opportunityDetail, /Ouvrir le visuel original/);
  assert.doesNotMatch(css, /catalog-media-natural/);
});


test("v79 refresh JWT distingue expiration et indisponibilite temporaire", () => {
  const api = read("lib/api.ts");
  const auth = read("hooks/useAuth.ts");
  assert.match(api, /response\.status === 401 \|\| response\.status === 403/);
  assert.match(api, /lastRefreshFailure = "invalid"/);
  assert.match(api, /lastRefreshFailure = "unavailable"/);
  assert.match(auth, /session\.reason !== "unavailable"/);
});

test("v79 uploads et telechargements critiques sont bornes", () => {
  const api = read("lib/api.ts");
  const multipart = read("lib/directMultipartUpload.ts");
  assert.match(api, /NEXT_PUBLIC_UPLOAD_TIMEOUT_MS/);
  assert.match(api, /xhr\.timeout = UPLOAD_TIMEOUT_MS/);
  assert.match(api, /xhr\.ontimeout/);
  assert.match(api, /fetchWithTimeout\(`\$\{API_URL\}\$\{path\}`/);
  assert.match(multipart, /NEXT_PUBLIC_UPLOAD_PART_TIMEOUT_MS/);
  assert.match(multipart, /xhr\.timeout = UPLOAD_PART_TIMEOUT_MS/);
});

test("v79 erreurs serveur exposent une reference de correlation", () => {
  const api = read("lib/api.ts");
  assert.match(api, /X-Request-ID/);
  assert.match(api, /Référence/);
  assert.match(api, /requestId/);
});
