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

test('workspace recruteur v75 expose branding, ATS et vivier', () => {
  const dashboard = read('app/dashboard/employer/page.tsx');
  assert.match(dashboard, /banner/);
  assert.match(dashboard, /logo/);
  assert.match(dashboard, /brand_color/);
  assert.match(dashboard, /screening_questions/);
  assert.match(dashboard, /recruiter_rating/);
  assert.match(dashboard, /recruiter_tags/);
  assert.match(dashboard, /next_step_at/);
  assert.match(dashboard, /talent-bookmarks/);
  assert.match(dashboard, /Pipeline/);
});

test('offres et page entreprise affichent les visuels publics', () => {
  assert.match(read('components/opportunities/OpportunityCard.tsx'), /cover_image/);
  assert.match(read('app/opportunities/[slug]/page.tsx'), /screening_answers/);
  const company = read('app/companies/[slug]/page.tsx');
  assert.match(company, /company\.banner/);
  assert.match(company, /company\.logo/);
  assert.match(company, /benefits/);
  assert.match(company, /values/);
});
