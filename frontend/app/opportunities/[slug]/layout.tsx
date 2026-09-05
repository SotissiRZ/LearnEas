import type { Metadata } from "next";
import { safePublicGet } from "@/lib/serverPublicApi";
import type { Opportunity } from "@/types/opportunities";

const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000").replace(/\/$/, "");

function absoluteUrl(value?: string | null): string | undefined {
  if (!value) return undefined;
  try { return new URL(value, SITE_URL).toString(); } catch { return undefined; }
}

function plainDescription(value: string): string {
  return value.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim().slice(0, 5000);
}

async function getOpportunity(slug: string): Promise<Opportunity | null> {
  const { data, ok } = await safePublicGet<Opportunity | null>(`/opportunities/listings/${encodeURIComponent(slug)}/`, null, 30);
  return ok ? data : null;
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const item = await getOpportunity(slug);
  if (!item) return { title: "Opportunité | KalanPro", robots: { index: false, follow: true } };
  const description = plainDescription(item.description).slice(0, 180);
  const canonical = `${SITE_URL}/opportunities/${encodeURIComponent(item.slug)}`;
  const image = absoluteUrl(item.cover_image || item.employer.logo);
  return {
    title: `${item.title} chez ${item.employer.company_name} | KalanPro`,
    description,
    alternates: { canonical },
    openGraph: {
      type: "website",
      url: canonical,
      title: `${item.title} chez ${item.employer.company_name}`,
      description,
      images: image ? [{ url: image }] : undefined,
    },
  };
}

function jobPosting(item: Opportunity) {
  const workType: Record<string, string> = {
    full_time: "FULL_TIME",
    part_time: "PART_TIME",
    fixed_term: "TEMPORARY",
    permanent: "FULL_TIME",
    internship: "INTERN",
    freelance: "CONTRACTOR",
    project: "CONTRACTOR",
  };
  const unitText: Record<string, string> = { hour: "HOUR", day: "DAY", month: "MONTH", year: "YEAR", project: "PROJECT" };
  const schema: Record<string, unknown> = {
    "@context": "https://schema.org",
    "@type": "JobPosting",
    title: item.title,
    description: plainDescription(item.description),
    datePosted: item.published_at || item.created_at,
    validThrough: item.application_deadline || undefined,
    employmentType: workType[item.contract_type] || (item.kind === "internship" ? "INTERN" : item.kind === "freelance" || item.kind === "mission" ? "CONTRACTOR" : undefined),
    identifier: { "@type": "PropertyValue", name: item.employer.company_name, value: `KALANPRO-${item.id}` },
    hiringOrganization: {
      "@type": "Organization",
      name: item.employer.company_name,
      sameAs: absoluteUrl(item.employer.website_url),
      logo: absoluteUrl(item.employer.logo),
    },
    directApply: item.apply_mode === "internal",
  };

  if (item.remote_worldwide || item.work_mode === "remote") {
    schema.jobLocationType = "TELECOMMUTE";
    if (item.country) schema.applicantLocationRequirements = { "@type": "Country", name: item.country };
  } else if (item.country || item.city) {
    schema.jobLocation = {
      "@type": "Place",
      address: {
        "@type": "PostalAddress",
        addressLocality: item.city || undefined,
        addressCountry: item.country || undefined,
      },
    };
  }

  if (item.show_salary && (item.salary_min || item.salary_max)) {
    const minValue = item.salary_min ? Number(item.salary_min) : undefined;
    const maxValue = item.salary_max ? Number(item.salary_max) : undefined;
    schema.baseSalary = {
      "@type": "MonetaryAmount",
      currency: item.salary_currency,
      value: {
        "@type": "QuantitativeValue",
        minValue: Number.isFinite(minValue) ? minValue : undefined,
        maxValue: Number.isFinite(maxValue) ? maxValue : undefined,
        value: minValue === maxValue && Number.isFinite(minValue) ? minValue : undefined,
        unitText: unitText[item.salary_period] || undefined,
      },
    };
  }
  return schema;
}

export default async function OpportunityLayout({ children, params }: { children: React.ReactNode; params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const item = await getOpportunity(slug);
  const json = item ? JSON.stringify(jobPosting(item)).replace(/</g, "\\u003c") : null;
  return <>
    {json && <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: json }} />}
    {children}
  </>;
}
