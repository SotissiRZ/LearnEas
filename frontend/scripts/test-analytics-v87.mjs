import fs from "node:fs";
import test from "node:test";
import assert from "node:assert/strict";

const backendModels = fs.readFileSync("../backend/apps/analytics/models.py", "utf8");
const backendServices = fs.readFileSync("../backend/apps/analytics/services.py", "utf8");
const backendViews = fs.readFileSync("../backend/apps/analytics/views.py", "utf8");
const backendThrottles = fs.readFileSync("../backend/apps/common/throttles.py", "utf8");
const adminPage = fs.readFileSync("app/dashboard/admin/page.tsx", "utf8");
const tracker = fs.readFileSync("lib/analytics.ts", "utf8");
const layoutTracker = fs.readFileSync("components/layout/ProductAnalytics.tsx", "utf8");

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
  const search = fs.readFileSync("components/discovery/SearchClient.tsx", "utf8");
  assert.match(search, /query_length/);
  assert.doesNotMatch(search, /trackProductEvent\([^\n]+query:/);
});
