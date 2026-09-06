import type { Metadata } from "next";
import { safePublicGet } from "@/lib/serverPublicApi";
import PricingPageClient, { type PublicPricingSettings } from "@/components/pricing/PricingPageClient";

export const metadata: Metadata = {
  title: "Tarifs | KalanPro",
  description: "Tarifs KalanPro pour apprenants, instructeurs, mentors et entreprises.",
};

const fallback: PublicPricingSettings = {
  pricing_enabled: true,
  platform_commission_percent: 15,
  learner_premium_enabled: true,
  learner_premium_monthly_eur: "9.99",
  instructor_pro_monthly_eur: "15.09",
  instructor_pro_commission_percent: 8,
  mentor_commission_percent: 15,
  employer_free_active_jobs: 1,
  employer_single_post_eur: "11.43",
  employer_pro_monthly_eur: "30.34",
  employer_pro_active_jobs: 5,
  employer_business_monthly_eur: "76.07",
  employer_business_active_jobs: 20,
};

export default async function PricingPage() {
  const { data } = await safePublicGet<PublicPricingSettings>("/auth/platform-settings/", fallback, 60);
  return <PricingPageClient settings={data} />;
}
