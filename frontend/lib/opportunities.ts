import type { JobApplicationStatus, Opportunity, OpportunityExperience, OpportunityKind, OpportunityStatus, OpportunityWorkMode } from "@/types";

export const OPPORTUNITY_KIND_LABELS: Record<OpportunityKind,string> = {
  job:"Emploi", internship:"Stage", freelance:"Mission freelance", apprenticeship:"Alternance", volunteer:"Volontariat",
};
export const WORK_MODE_LABELS: Record<OpportunityWorkMode,string> = { remote:"À distance", hybrid:"Hybride", onsite:"Sur site" };
export const EXPERIENCE_LABELS: Record<OpportunityExperience,string> = { entry:"Débutant / premier poste", junior:"Junior", mid:"Intermédiaire", senior:"Senior", lead:"Lead / management" };
export const OPPORTUNITY_STATUS_LABELS: Record<OpportunityStatus,string> = { draft:"Brouillon", pending_review:"En validation", published:"Publiée", rejected:"Refusée", closed:"Clôturée", filled:"Pourvue" };
export const APPLICATION_STATUS_LABELS: Record<JobApplicationStatus,string> = { submitted:"Envoyée", reviewing:"En étude", shortlisted:"Présélectionnée", interview:"Entretien", offer:"Offre reçue", hired:"Recruté(e)", rejected:"Non retenue", withdrawn:"Retirée" };

export function salaryLabel(o: Pick<Opportunity,"salary_min"|"salary_max"|"salary_currency"|"compensation_period"|"salary_visible">): string {
  if (!o.salary_visible) return "Rémunération non publiée";
  const min=o.salary_min?Number(o.salary_min):null, max=o.salary_max?Number(o.salary_max):null;
  if(min===null&&max===null)return "Rémunération à discuter";
  const fmt=(n:number)=>new Intl.NumberFormat("fr-FR",{maximumFractionDigits:2}).format(n);
  const period={hour:"/ heure",month:"/ mois",year:"/ an",project:"/ projet"}[o.compensation_period]||"";
  if(min!==null&&max!==null)return `${fmt(min)} – ${fmt(max)} ${o.salary_currency} ${period}`;
  if(min!==null)return `À partir de ${fmt(min)} ${o.salary_currency} ${period}`;
  return `Jusqu'à ${fmt(max||0)} ${o.salary_currency} ${period}`;
}

export function statusBadge(status:string){
  if(["published","hired","offer"].includes(status)) return "bg-emerald-50 text-emerald-700";
  if(["pending_review","reviewing","interview","shortlisted","submitted"].includes(status)) return "bg-amber-50 text-amber-700";
  if(["rejected","withdrawn"].includes(status)) return "bg-red-50 text-red-700";
  return "bg-gray-100 text-gray-600";
}
