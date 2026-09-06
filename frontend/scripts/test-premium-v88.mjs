import test from "node:test";
import assert from "node:assert/strict";
import { readFrontend, readRepo } from "./test-paths.mjs";

const accountModels = readRepo("backend/apps/accounts/models.py");
const catalogModels = readRepo("backend/apps/catalog/models.py");
const enrollmentModels = readRepo("backend/apps/enrollments/models.py");
const enrollmentSerializers = readRepo("backend/apps/enrollments/serializers.py");
const paymentModels = readRepo("backend/apps/payments/models.py");
const paymentSerializers = readRepo("backend/apps/payments/serializers.py");
const paymentViews = readRepo("backend/apps/payments/views.py");
const subscriptions = readRepo("backend/apps/payments/subscriptions.py");
const paymentServices = readRepo("backend/apps/payments/services.py");
const pricing = readFrontend("components/pricing/PricingPageClient.tsx");
const premiumAction = readFrontend("components/course/PremiumAccessAction.tsx");
const checkout = readFrontend("app/checkout/page.tsx");
const admin = readFrontend("app/dashboard/admin/page.tsx");
const studentDashboard = readFrontend("app/dashboard/student/page.tsx");
const studentPdfDashboard = readFrontend("app/dashboard/student/pdfs/page.tsx");
const courseFilters = readFrontend("components/course/CourseFilters.tsx");

test("v88 Premium apprenant est tarifable et administrable sans remplacer l'achat unitaire", () => {
  assert.match(accountModels, /learner_premium_monthly_eur\s*=\s*models\.DecimalField/);
  assert.match(accountModels, /learner_premium_enabled\s*=\s*models\.BooleanField/);
  assert.match(catalogModels, /premium_included\s*=\s*models\.BooleanField/g);
  assert.match(admin, /KalanPro Premium apprenant/);
  assert.match(admin, /premium_included: v/);
  assert.match(pricing, /[Aa]chat à l[’'"]unité/);
  assert.match(pricing, /Premium/);
});

test("v88 abonnement est un entitlement temporaire chaîné et idempotent par commande", () => {
  assert.match(paymentModels, /LEARNER_SUBSCRIPTION\s*=\s*"learner_subscription"/);
  assert.match(paymentModels, /class LearnerSubscription/);
  assert.match(paymentModels, /source_order\s*=\s*models\.OneToOneField/);
  assert.match(paymentModels, /starts_at__lte=now/);
  assert.match(subscriptions, /PREMIUM_PERIOD_DAYS\s*=\s*30/);
  assert.match(subscriptions, /max\(now, latest_end\)/);
  assert.match(subscriptions, /filter\(source_order=order\)\.first\(\)/);
  assert.match(subscriptions, /premium_coverage_end/);
});

test("v88 accès Premium expire automatiquement mais un achat définitif reste permanent", () => {
  assert.match(enrollmentModels, /access_expires_at__isnull=True/);
  assert.match(enrollmentModels, /access_expires_at__gt=now/);
  assert.match(enrollmentModels, /source_subscription\s*=\s*models\.ForeignKey/g);
  assert.match(paymentViews, /access_expires_at__isnull=True/);
  assert.match(paymentViews, /source_subscription\s*=\s*None/);
  assert.match(paymentViews, /access_expires_at\s*=\s*None/);
  assert.match(enrollmentSerializers, /"access_expires_at"/);
  assert.match(studentDashboard, /Premium · accès jusqu/);
  assert.match(studentPdfDashboard, /Premium · jusqu/);
});

test("v88 remboursement révoque la période concernée et recalcule les droits temporaires", () => {
  assert.match(paymentServices, /revoke_learner_subscription/);
  assert.match(subscriptions, /subscription\.revoked_at\s*=\s*now/);
  assert.match(subscriptions, /period\.starts_at\s*-=\s*duration/);
  assert.match(subscriptions, /period\.ends_at\s*-=\s*duration/);
  assert.match(subscriptions, /_refresh_subscription_entitlements\(subscription\.user\)/);
});

test("v88 checkout Premium est dédié, idempotent et exclut cohortes et mentorat", () => {
  assert.match(paymentSerializers, /learner_product\s*=\s*serializers\.ChoiceField\(choices=\["premium"\]/);
  assert.match(paymentSerializers, /Un abonnement apprenant doit être acheté dans une commande dédiée/);
  assert.match(paymentViews, /\(employer_product or learner_product\) and not idempotency_key/);
  assert.match(paymentViews, /learner_product and user\.role != "student"/);
  assert.match(paymentViews, /ItemType\.LEARNER_SUBSCRIPTION/);
  assert.match(checkout, /learner_product:\s*learnerProduct/);
  assert.match(pricing, /Les cohortes live et le mentorat restent (?:hors Premium|facturés séparément)/);
});

test("v88 catalogue Premium nécessite un abonnement actif et un contenu explicitement inclus", () => {
  assert.match(subscriptions, /active_learner_subscription\(user\)/);
  assert.match(subscriptions, /published=True, premium_included=True/);
  assert.match(paymentViews, /class PremiumAccessView\(APIView\)/);
  assert.match(premiumAction, /\/payments\/premium\//);
  assert.match(premiumAction, /Accéder avec Premium/);
  assert.match(courseFilters, /premium_included/);
  assert.match(studentDashboard, /KalanPro Premium actif/);
  assert.match(studentDashboard, /courses\?premium_included=true/);
});

test("v88 fournit les migrations des quatre domaines impactés", () => {
  for (const file of [
    "backend/apps/accounts/migrations/0012_learner_premium_pricing.py",
    "backend/apps/catalog/migrations/0008_premium_catalog.py",
    "backend/apps/payments/migrations/0016_learner_subscription.py",
    "backend/apps/enrollments/migrations/0008_subscription_entitlements.py",
  ]) {
    const migration = readRepo(file);
    assert.match(migration, /class Migration\(migrations\.Migration\)/);
  }
});
