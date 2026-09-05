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
  const visibleSkills = opportunity.skills_required.slice(0, 3);
  const remainingSkills = Math.max(0, opportunity.skills_required.length - visibleSkills.length);

  return (
    <Link href={`/opportunities/${opportunity.slug}`} className="card catalog-card group flex flex-col overflow-hidden transition hover:-translate-y-0.5 hover:shadow-soft">
      <div className="relative aspect-[16/10] w-full overflow-hidden bg-gradient-to-br from-navy-950 via-navy-900 to-brand-900">
        {opportunity.cover_image ? (
          <img loading="lazy" decoding="async" src={opportunity.cover_image} alt={opportunity.title} className="h-full w-full object-cover object-center transition duration-300 group-hover:scale-[1.025]" />
        ) : (
          <div className="grid h-full place-items-center bg-[radial-gradient(circle_at_70%_20%,rgba(255,100,26,.22),transparent_35%)]">
            {opportunity.employer.logo ? (
              <div className="grid h-20 w-20 place-items-center overflow-hidden rounded-2xl border border-white/20 bg-white/95 p-2 shadow-xl">
                <img loading="lazy" decoding="async" src={opportunity.employer.logo} alt={`Logo ${opportunity.employer.company_name}`} className="h-full w-full object-contain" />
              </div>
            ) : <BriefcaseBusiness size={46} className="text-white/70" />}
          </div>
        )}
        {opportunity.cover_image && (
          <span className="pointer-events-none absolute bottom-2.5 right-2.5 rounded-full bg-navy-950/80 px-2.5 py-1 text-[10px] font-bold text-white opacity-0 shadow-sm backdrop-blur transition group-hover:opacity-100">Voir le visuel complet</span>
        )}
      </div>

      <div className="flex flex-1 flex-col p-3.5 sm:p-4">
        <div className="flex items-center justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2.5">
            <div className="grid h-9 w-9 shrink-0 place-items-center overflow-hidden rounded-lg bg-brand-50 text-brand-700">
              {opportunity.employer.logo ? <img loading="lazy" decoding="async" src={opportunity.employer.logo} alt="" className="h-full w-full object-contain p-0.5" /> : <BriefcaseBusiness size={17} />}
            </div>
            <div className="min-w-0">
              <p className="truncate text-xs font-bold text-slate-700">{opportunity.employer.company_name}</p>
              {opportunity.department && <p className="truncate text-[10px] text-slate-400">{opportunity.department}</p>}
            </div>
          </div>
          <div className="flex shrink-0 flex-wrap justify-end gap-1.5">
            <span className="badge !px-2 !py-1 bg-brand-50 text-brand-700">{kindLabel[opportunity.kind] || opportunity.kind}</span>
            {typeof opportunity.match_score === "number" && <span className="badge !px-2 !py-1 bg-violet-50 text-violet-700">{opportunity.match_score}%</span>}
          </div>
        </div>

        <h2 className="mt-2.5 line-clamp-2 text-[1.05rem] font-extrabold leading-snug text-navy-950 group-hover:text-brand-700">{opportunity.title}</h2>

        <div className="mt-2.5 grid grid-cols-2 gap-x-3 gap-y-1.5 text-[11px] text-gray-500">
          <span className="flex min-w-0 items-center gap-1.5"><Radio size={12} className="shrink-0" /> <span className="truncate">{modeLabel[opportunity.work_mode] || opportunity.work_mode}</span></span>
          {location && <span className="flex min-w-0 items-center gap-1.5"><MapPin size={12} className="shrink-0" /> <span className="truncate">{location}</span></span>}
          {opportunity.application_deadline && <span className="col-span-2 flex items-center gap-1.5"><Clock3 size={12} className="shrink-0" /> avant le {new Date(opportunity.application_deadline).toLocaleDateString("fr-FR")}</span>}
          {opportunity.openings > 1 && <span className="col-span-2 flex items-center gap-1.5"><UsersRound size={12} className="shrink-0" /> {opportunity.openings} postes</span>}
        </div>

        {visibleSkills.length > 0 && <div className="mt-2.5 flex flex-wrap gap-1.5">
          {visibleSkills.map((skill) => <span key={skill} className="rounded-full bg-gray-100 px-2 py-1 text-[10px] font-medium text-gray-600">{skill}</span>)}
          {remainingSkills > 0 && <span className="rounded-full bg-slate-50 px-2 py-1 text-[10px] font-semibold text-slate-400">+{remainingSkills}</span>}
        </div>}

        <div className="mt-3 flex items-center justify-between gap-2 border-t border-slate-100 pt-2.5">
          <span className="min-w-0 text-[13px] font-extrabold text-ink">{salary(opportunity)}</span>
          {opportunity.featured && <span className="shrink-0 text-amber-600" title="À la une"><Sparkles size={15} /></span>}
        </div>
      </div>
    </Link>
  );
}
