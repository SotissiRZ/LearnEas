import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const read = (p) => fs.readFileSync(new URL(`../${p}`, import.meta.url), 'utf8');

test('type utilisateur frontend inclut employer', () => {
  assert.match(read('types/index.ts'), /role:\s*"admin"\s*\|\s*"instructor"\s*\|\s*"student"\s*\|\s*"employer"/);
});

test('inscription propose un parcours entreprise et collecte son identité', () => {
  const source = read('app/register/page.tsx');
  assert.match(source, /type PublicRole = "student" \| "employer"/);
  assert.match(source, /company_name/);
  assert.match(source, /Créer mon espace entreprise/);
});

test('login et navigation envoient employer vers son dashboard', () => {
  assert.match(read('app/login/page.tsx'), /user\.role === "employer"/);
  assert.match(read('components/layout/Navbar.tsx'), /user\?\.role === "employer" \? "\/dashboard\/employer"/);
  assert.match(read('components/layout/NavigationPerformance.tsx'), /user\.role === "employer" \? "\/dashboard\/employer"/);
});

test('dashboard entreprise est protégé par le rôle employer', () => {
  assert.match(read('app/dashboard/employer/page.tsx'), /roles:\s*\["employer"\]/);
});
