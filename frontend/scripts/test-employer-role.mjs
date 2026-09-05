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

test('branding entreprise ne superpose plus le logo sur la bannière', () => {
  const dashboard = read('app/dashboard/employer/page.tsx');
  assert.doesNotMatch(dashboard, /-mt-10 ml-5 flex items-end/);
  assert.match(dashboard, /mt-5 flex flex-col gap-3 sm:flex-row sm:items-center/);
  assert.match(dashboard, /Le logo est affiché séparément de la bannière/);
});

test('v78 relie les offres recruteur au checkout self-service', () => {
  const pricing = read('components/pricing/PricingPageClient.tsx');
  const checkout = read('app/checkout/page.tsx');
  assert.match(pricing, /\/checkout\?employer_product=single_post/);
  assert.match(pricing, /\/checkout\?employer_product=pro/);
  assert.match(pricing, /\/checkout\?employer_product=business/);
  assert.match(checkout, /Idempotency-Key/);
  assert.match(checkout, /employer_product/);
  assert.match(checkout, /platform-settings/);
  assert.doesNotMatch(checkout, /amount:\s*employerAmount/);
});

test('v78 separe historique entretiens et offre dans le drawer ATS', () => {
  const dashboard = read('app/dashboard/employer/page.tsx');
  assert.match(dashboard, /applications\/\$\{app\.id\}\/\?recruiter=1/);
  assert.match(dashboard, /applications\/\$\{app\.id\}\/history\//);
  assert.match(dashboard, /applications\/\$\{app\.id\}\/interviews\//);
  assert.match(dashboard, /applications\/\$\{app\.id\}\/offer\//);
  assert.match(dashboard, /Promise\.allSettled/);
  assert.match(dashboard, /processError/);
  assert.match(dashboard, /remove_cover_image/);
});

test('v78 expose la reponse candidat et le journal des acces recruteur', () => {
  const student = read('app/dashboard/student/opportunities/page.tsx');
  assert.match(student, /offer-response/);
  assert.match(student, /talent-accesses/);
  assert.match(student, /Accepter/);
  assert.match(student, /Refuser/);
});

test('v78 publie un schema SEO JobPosting', () => {
  const layout = read('app/opportunities/[slug]/layout.tsx');
  assert.match(layout, /"@type": "JobPosting"/);
  assert.match(layout, /datePosted/);
  assert.match(layout, /hiringOrganization/);
  assert.match(layout, /baseSalary/);
  assert.match(layout, /jobLocationType/);
  assert.match(layout, /fixed_term: "TEMPORARY"/);
  assert.match(layout, /permanent: "FULL_TIME"/);
  assert.match(layout, /dangerouslySetInnerHTML/);
});

test('v78 checkout recruteur respecte les quotas configurables et le contrat entretien', () => {
  const checkout = read('app/checkout/page.tsx');
  const dashboard = read('app/dashboard/employer/page.tsx');
  assert.match(checkout, /employer_pro_active_jobs: number/);
  assert.match(checkout, /employer_business_active_jobs: number/);
  assert.match(checkout, /employerPricing\?\.employer_pro_active_jobs/);
  assert.match(checkout, /employerPricing\?\.employer_business_active_jobs/);
  assert.doesNotMatch(checkout, /detail: "5 offres actives/);
  assert.doesNotMatch(checkout, /detail: "20 offres actives/);
  const scheduleBlock = dashboard.slice(dashboard.indexOf('async function scheduleInterview'), dashboard.indexOf('async function saveOffer'));
  assert.doesNotMatch(scheduleBlock, /note:\s*""/);
  assert.match(scheduleBlock, /location_or_url: interviewLocation/);
});
