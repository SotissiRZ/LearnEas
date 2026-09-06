import type {
  JobApplicationStatus,
  Opportunity,
  OpportunityExperience,
  OpportunityKind,
  OpportunityStatus,
  OpportunityWorkMode,
} from "@/types";

export const OPPORTUNITY_KIND_LABELS: Record<OpportunityKind, string> = {
  job: "Emploi",
  internship: "Stage",
  freelance: "Mission freelance",
  mission: "Mission",
  apprenticeship: "Alternance",
  volunteer: "Volontariat",
};

export const OPPORTUNITY_WORK_MODE_LABELS: Record<OpportunityWorkMode, string> = {
  remote: "À distance",
  hybrid: "Hybride",
  onsite: "Sur site",
};
export const WORK_MODE_LABELS = OPPORTUNITY_WORK_MODE_LABELS;

export const OPPORTUNITY_EXPERIENCE_LABELS: Record<OpportunityExperience, string> = {
  entry: "Premier emploi",
  junior: "Junior",
  mid: "Intermédiaire",
  senior: "Senior",
  lead: "Lead / management",
};
export const EXPERIENCE_LABELS = OPPORTUNITY_EXPERIENCE_LABELS;

export const OPPORTUNITY_STATUS_LABELS: Record<OpportunityStatus, string> = {
  draft: "Brouillon",
  pending_review: "En validation",
  published: "Publiée",
  rejected: "Refusée",
  closed: "Clôturée",
  filled: "Pourvue",
  archived: "Archivée",
};

export const APPLICATION_STATUS_LABELS: Record<JobApplicationStatus, string> = {
  submitted: "Envoyée",
  reviewing: "En étude",
  shortlisted: "Présélectionnée",
  interview: "Entretien",
  offer: "Offre",
  hired: "Recruté(e)",
  rejected: "Non retenu(e)",
  withdrawn: "Retirée",
};

const PERIOD_LABELS: Record<"hour" | "month" | "year" | "project", string> = {
  hour: "/ heure",
  month: "/ mois",
  year: "/ an",
  project: "/ projet",
};

export function formatCompensation(o: Opportunity): string {
  if (o.show_salary === false) return "Rémunération non communiquée";

  const min = o.compensation_min ?? o.salary_min;
  const max = o.compensation_max ?? o.salary_max;
  if (min == null && max == null) return "Rémunération non communiquée";

  const currency = o.compensation_currency || o.salary_currency || "";
  const periodKey = o.compensation_period || (o.salary_period as keyof typeof PERIOD_LABELS | undefined);
  const period = periodKey ? PERIOD_LABELS[periodKey] || "" : "";
  const stringify = (value: string | number | null | undefined) => value == null ? "" : String(value);

  if (min != null && max != null && String(min) !== String(max)) {
    return `${stringify(min)} – ${stringify(max)} ${currency} ${period}`.replace(/\s+/g, " ").trim();
  }
  return `${stringify(min ?? max)} ${currency} ${period}`.replace(/\s+/g, " ").trim();
}

export const formatOpportunityCompensation = formatCompensation;

export function statusBadge(status: OpportunityStatus | JobApplicationStatus | string): string {
  if (["published", "hired"].includes(status)) return "bg-emerald-50 text-emerald-700";
  if (["pending_review", "reviewing"].includes(status)) return "bg-blue-50 text-blue-700";
  if (["shortlisted"].includes(status)) return "bg-violet-50 text-violet-700";
  if (["interview"].includes(status)) return "bg-amber-50 text-amber-800";
  if (["offer"].includes(status)) return "bg-cyan-50 text-cyan-700";
  if (["rejected"].includes(status)) return "bg-red-50 text-red-700";
  if (["closed", "filled", "archived", "withdrawn"].includes(status)) return "bg-gray-100 text-gray-600";
  return "bg-slate-100 text-slate-700";
}
