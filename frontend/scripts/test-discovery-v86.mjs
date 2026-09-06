import { readFrontend, readRepo } from "./test-paths.mjs";
import test from "node:test";
import assert from "node:assert/strict";

const page = readFrontend("components/discovery/SearchClient.tsx");
const nav = readFrontend("components/layout/Navbar.tsx");
const types = readFrontend("types/discovery.ts");
const backendViews = readRepo("backend/apps/discovery/views.py");
const backendServices = readRepo("backend/apps/discovery/services.py");

test("v86 recherche globale couvre les catalogues principaux", () => {
  assert.match(page, /\/discovery\/search\//);
  assert.match(types, /course.*formation.*pdf.*mentor.*opportunity.*company.*talent/s);
});

test("v86 recommandations utilisent le profil sans rendre le talent public", () => {
  assert.match(page, /\/discovery\/recommendations\//);
  assert.match(backendServices, /employer_has_talent_pool_access/);
  assert.match(backendViews, /allow_talents/);
});

test("v86 barre de navigation envoie vers la recherche unifiee et suggere des resultats", () => {
  assert.match(nav, /\/search\?q=/);
  assert.match(nav, /\/discovery\/search\/suggestions\//);
});

test("v86 cartes de recherche restent economes sur mobile", () => {
  assert.match(page, /loading="lazy"/);
  assert.match(page, /decoding="async"/);
});
