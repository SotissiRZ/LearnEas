import Link from "next/link";
import { BriefcaseBusiness, Clock3, MapPin, Radio, Sparkles, UsersRound } from "lucide-react";
import type { Opportunity } from "@/types/opportunities";

const kindLabel: Record<string, string> = { job: "Emploi", internship: "Stage", freelance: "Freelance", mission: "Mission" };
const modeLabel: Record<string, string> = { remote: "À distance", hybrid: "Hybride", onsite: "Sur site" };
const periodLabel: Record<string, string> = { hour: "/ heure", day: "/ jour", month: "/ mois", year: "/ an", project: "forfait mission" };

function salary(opportunity: Opportunity) {
  if (!opportunity.show_salary || (!opportunity.salary_min && !opportunity.salary_max)) return "Rémunération non publiée";
  const fmt = (value: string | null) => value ? Number(value).toLocaleString("fr-FR", { maximumFractionDigits: 0 }) : "";
  if (opportunity.salary_min && opportunity.salary_max) return `${fmt(opportunity.salary_min)}–${fmt(opportunity.salary_max)} ${opportunity.salary_currency} ${periodLabel[opportunity.salary_period] || ""}`;
  return `${opportunity.salary_min ? "Dès " : "Jusqu’à "}${fmt(opportunity.salary_min || opportunity.salary_max)} ${opportunity.salary_currency} ${periodLabel[opportunity.salary_period] || ""}`;
}

export default function OpportunityCard({ opportunity }: { opportunity: Opportunity }) {
  const location = opportunity.remote_worldwide ? "Monde entier" : [opportunity.city, opportunity.country].filter(Boolean).join(", ");
  return <Link href={`/opportunities/${opportunity.slug}`} className="card group flex h-full flex-col overflow-hidden transition hover:-translate-y-0.5 hover:shadow-soft">
    {opportunity.cover_image && <div className="aspect-[16/7] overflow-hidden bg-slate-100"><img loading="lazy" decoding="async" src={opportunity.cover_image} alt="" className="h-full w-full object-cover transition duration-300 group-hover:scale-[1.02]" /></div>}
    <div className="flex h-full flex-col p-5"><div className="flex items-start gap-3"><div className="grid h-12 w-12 shrink-0 place-items-center overflow-hidden rounded-xl bg-brand-50 text-brand-700">{opportunity.employer.logo ? <img loading="lazy" decoding="async" src={opportunity.employer.logo} alt="" className="h-full w-full object-contain p-0.5" /> : <BriefcaseBusiness size={21} />}</div><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><span className="badge bg-brand-50 text-brand-700">{kindLabel[opportunity.kind] || opportunity.kind}</span>{opportunity.featured && <span className="badge bg-amber-50 text-amber-700"><Sparkles size={11} /> À la une</span>}{typeof opportunity.match_score === "number" && <span className="badge bg-violet-50 text-violet-700">Match {opportunity.match_score}%</span>}</div><h2 className="mt-2 line-clamp-2 text-lg font-bold group-hover:text-brand-700">{opportunity.title}</h2><p className="mt-1 text-sm font-medium text-gray-600">{opportunity.employer.company_name}</p>{opportunity.department && <p className="mt-0.5 text-[11px] text-slate-400">{opportunity.department}</p>}</div></div><div className="mt-4 flex flex-wrap gap-x-4 gap-y-2 text-xs text-gray-500"><span className="flex items-center gap-1"><Radio size={13} /> {modeLabel[opportunity.work_mode] || opportunity.work_mode}</span>{location && <span className="flex items-center gap-1"><MapPin size={13} /> {location}</span>}{opportunity.openings > 1 && <span className="flex items-center gap-1"><UsersRound size={13}/> {opportunity.openings} postes</span>}{opportunity.application_deadline && <span className="flex items-center gap-1"><Clock3 size={13} /> avant le {new Date(opportunity.application_deadline).toLocaleDateString("fr-FR")}</span>}</div><div className="mt-4 flex flex-wrap gap-1.5">{opportunity.skills_required.slice(0, 5).map((skill) => <span key={skill} className="rounded-full bg-gray-100 px-2 py-1 text-[11px] font-medium text-gray-600">{skill}</span>)}</div><div className="mt-auto pt-5 text-sm font-semibold text-ink">{salary(opportunity)}</div></div>
  </Link>;
}
