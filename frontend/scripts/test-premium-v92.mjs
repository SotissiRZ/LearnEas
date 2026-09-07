import test from "node:test";
import assert from "node:assert/strict";
import { readFrontend, readRepo } from "./test-paths.mjs";

const paymentModels = readRepo("backend/apps/payments/models.py");
const subscriptions = readRepo("backend/apps/payments/subscriptions.py");
const paymentTasks = readRepo("backend/apps/payments/tasks.py");
const paymentUrls = readRepo("backend/apps/payments/urls.py");
const paymentMigration = readRepo("backend/apps/payments/migrations/0017_premium_lifecycle_revenue.py");
const accountMigration = readRepo("backend/apps/accounts/migrations/0013_premium_creator_pool.py");
const settings = readRepo("backend/learneas/settings.py");
const operations = readRepo("backend/apps/common/operations.py");
const premiumReport = readRepo("backend/apps/payments/management/commands/premium_revenue_report.py");
const composeDev = readRepo("docker-compose.dev.yml");
const composeProd = readRepo("docker-compose.yml");
const student = readFrontend("app/dashboard/student/page.tsx");
const instructorFinance = readFrontend("app/dashboard/instructor/finance/page.tsx");
const admin = readFrontend("app/dashboard/admin/page.tsx");
const pricing = readFrontend("components/pricing/PricingPageClient.tsx");

test("v92 ajoute un cycle Premium sans prétendre débiter hors session", () => {
  assert.match(paymentModels, /class PremiumRenewalProfile\(/);
  assert.match(subscriptions, /def configure_premium_renewal\(/);
  assert.match(subscriptions, /def prepare_premium_renewal\(/);
  assert.match(subscriptions, /"automatic_charge": False/);
  assert.match(subscriptions, /checkout_confirmation_required/);
  assert.match(paymentModels, /grace_ends_at/);
  assert.match(subscriptions, /PREMIUM_RENEWAL_GRACE_HOURS/);
  assert.match(subscriptions, /reason": "grace_expired"/);
  assert.doesNotMatch(subscriptions, /card_number|cvv|cvc|payment_method_token\s*=/i);
  assert.match(paymentUrls, /premium\/renewal\//);
  assert.match(student, /\/payments\/premium\/renewal\//);
  assert.match(student, /confirmer|confirmation/i);
});

test("v92 distribue le pool Premium par usage et garde un ledger réversible", () => {
  assert.match(paymentModels, /class PremiumContentUsage\(/);
  assert.match(paymentModels, /class PremiumRevenueAllocation\(/);
  assert.match(paymentModels, /PREMIUM = "premium"/);
  assert.match(paymentModels, /PREMIUM_REFUND = "premium_refund"/);
  assert.match(subscriptions, /def record_premium_usage\(/);
  assert.match(subscriptions, /def settle_premium_subscription\(/);
  assert.match(subscriptions, /def reverse_premium_revenue\(/);
  assert.match(subscriptions, /entry_type=InstructorLedgerEntry\.EntryType\.PREMIUM_REFUND/);
  assert.match(paymentMigration, /PremiumRevenueAllocation/);
  assert.match(paymentMigration, /uniq_ledger_premium_alloc_type/);
});

test("v92 rend le pool créateurs administrable et visible", () => {
  assert.match(accountMigration, /learner_premium_creator_pool_percent/);
  assert.match(admin, /Pool Premium créateurs/);
  assert.match(pricing, /learner_premium_creator_pool_percent/);
  assert.match(instructorFinance, /Revenus KalanPro Premium/);
  assert.match(instructorFinance, /premium_creator_pool_percent/);
  assert.match(instructorFinance, /recent_premium_allocations/);
});

test("v92 planifie renouvellement et settlement via Celery avec bornes", () => {
  assert.match(paymentTasks, /prepare_premium_renewals/);
  assert.match(paymentTasks, /settle_premium_revenue/);
  assert.match(settings, /PREMIUM_RENEWAL_LEAD_HOURS/);
  assert.match(settings, /PREMIUM_RENEWAL_GRACE_HOURS/);
  assert.match(settings, /PREMIUM_RENEWAL_BATCH_SIZE/);
  assert.match(settings, /PREMIUM_SETTLEMENT_BATCH_SIZE/);
  assert.match(settings, /apps\.payments\.tasks\.prepare_premium_renewals/);
  assert.match(settings, /apps\.payments\.tasks\.settle_premium_revenue/);
  assert.match(composeDev, /PREMIUM_RENEWAL_GRACE_HOURS/);
  assert.match(composeDev, /PREMIUM_SETTLEMENT_BATCH_SIZE/);
  assert.match(composeProd, /PREMIUM_RENEWAL_GRACE_HOURS/);
});


test("v92 expose les retards Premium dans la santé plateforme", () => {
  assert.match(operations, /premium_renewal_action_required/);
  assert.match(operations, /premium_renewal_past_due/);
  assert.match(operations, /premium_unsettled_periods/);
  assert.match(admin, /Premium à confirmer/);
  assert.match(admin, /Périodes à répartir/);
});


test("v92 fournit un rapport opérable du cycle Premium", () => {
  assert.match(premiumReport, /premium_revenue_report|Résumé opérationnel V92|creator_pool_percent/);
  assert.match(premiumReport, /fail-on-past-due/);
  assert.match(premiumReport, /automatic_charge.*False/s);
});
