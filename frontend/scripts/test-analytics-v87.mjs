import { readFrontend, readRepo } from "./test-paths.mjs";
import test from "node:test";
import assert from "node:assert/strict";

const backendModels = readRepo("backend/apps/analytics/models.py");
const backendServices = readRepo("backend/apps/analytics/services.py");
const backendViews = readRepo("backend/apps/analytics/views.py");
const backendThrottles = readRepo("backend/apps/common/throttles.py");
const adminPage = readFrontend("app/dashboard/admin/page.tsx");
const tracker = readFrontend("lib/analytics.ts");
const layoutTracker = readFrontend("components/layout/ProductAnalytics.tsx");

 test("v87 stocke des evenements produit minimises sans requete sensible", () => {
  assert.match(backendModels, /class ProductEvent/);
  assert.match(backendServices, /ALLOWED_PROPERTY_KEYS/);
  assert.match(backendServices, /split\("\?", 1\)/);
  assert.match(backendServices, /sha256/);
  assert.doesNotMatch(backendServices, /"email".*ALLOWED_PROPERTY_KEYS/s);
  assert.match(backendThrottles, /class ProductAnalyticsRateThrottle\(UserRateThrottle\)/);
});

test("v87 dashboard admin couvre acquisition finance learning recrutement retention", () => {
  assert.match(backendServices, /"acquisition"/);
  assert.match(backendServices, /"finance"/);
  assert.match(backendServices, /"learning"/);
  assert.match(backendServices, /"recruitment"/);
  assert.match(backendServices, /retention_rate/);
  assert.match(adminPage, /Analytics produit/);
  assert.match(adminPage, /Tunnel commercial/);
  assert.match(adminPage, /Tunnel recrutement/);
});

test("v87 export CSV est admin-only et agrege", () => {
  assert.match(backendViews, /class AdminAnalyticsExportView/);
  assert.match(backendViews, /permission_classes = \[IsAdminRole\]/);
  assert.match(adminPage, /kalanpro-analytics-/);
});

test("v87 navigation et recherche emettent des signaux sans stocker la query", () => {
  assert.match(tracker, /sessionStorage/);
  assert.match(layoutTracker, /trackProductEvent/);
  assert.doesNotMatch(layoutTracker, /searchParams|window\.location\.search/);
  assert.match(layoutTracker, /PRIVATE_PREFIXES/);
  const search = readFrontend("components/discovery/SearchClient.tsx");
  assert.match(search, /query_length/);
  assert.doesNotMatch(search, /trackProductEvent\([^\n]+query:/);
});
