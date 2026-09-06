import test from "node:test";
import assert from "node:assert/strict";
import { readFrontend } from "./test-paths.mjs";

test("v88 maintient le contrat TypeScript recrutement et tarifs admin", () => {
  const index = readFrontend("types/index.ts");
  const opportunities = readFrontend("types/opportunities.ts");
  const admin = readFrontend("app/dashboard/admin/page.tsx");
  const countries = readFrontend("components/ui/CountryMultiSelect.tsx");
  const legacyOpportunityLib = readFrontend("lib/opportunities.ts");

  assert.match(index, /export \* from ["']\.\/opportunities["']/);
  for (const symbol of [
    "CompanyProfile", "EmployerJobApplication", "JobApplicationStatus", "OpportunityExperience",
    "OpportunityKind", "OpportunityStatus", "OpportunityWorkMode", "Opportunity",
  ]) assert.match(opportunities, new RegExp(`export type ${symbol}\\b`));


  // Compatibilité avec les écrans opportunités historiques encore présents sur certaines installations.
  assert.match(opportunities, /\| "apprenticeship"/);
  assert.match(opportunities, /\| "volunteer"/);
  assert.match(opportunities, /\| "pending_review"/);
  assert.match(opportunities, /\| "rejected"/);
  assert.match(opportunities, /required_skills: string\[\]/);
  assert.match(opportunities, /company: CompanyProfile/);
  assert.match(opportunities, /compensation_period: "hour" \| "month" \| "year" \| "project"/);
  const employerDashboard = readFrontend("app/dashboard/employer/page.tsx");
  assert.match(employerDashboard, /pipelineStatuses: JobApplicationStatus\[\]/);
  assert.match(employerDashboard, /status: e\.target\.value as JobApplicationStatus/);


  assert.match(legacyOpportunityLib, /mission:\s*["']Mission["']/);
  assert.match(legacyOpportunityLib, /archived:\s*["']Archivée["']/);
  assert.match(legacyOpportunityLib, /OPPORTUNITY_KIND_LABELS: Record<OpportunityKind, string>/);
  assert.match(legacyOpportunityLib, /OPPORTUNITY_STATUS_LABELS: Record<OpportunityStatus, string>/);

  for (const field of [
    "pricing_enabled", "employer_free_active_jobs", "employer_single_post_eur",
    "employer_pro_monthly_eur", "employer_pro_active_jobs",
    "employer_business_monthly_eur", "employer_business_active_jobs",
  ]) assert.match(admin, new RegExp(`${field}:`));

  assert.match(countries, /new Set<string>\(PRIORITY_COUNTRY_CODES\)/);
});
