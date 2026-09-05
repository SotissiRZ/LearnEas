"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, BriefcaseBusiness, CheckCircle2, ExternalLink, Loader2, MapPin, Radio, Send, ShieldCheck } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import type { Opportunity, OpportunityApplication } from "@/types/opportunities";

const labels: Record<string, string> = { job: "Emploi", internship: "Stage", freelance: "Freelance", mission: "Mission", remote: "À distance", hybrid: "Hybride", onsite: "Sur site", entry: "Premier emploi", junior: "Junior", mid: "Intermédiaire", senior: "Senior", lead: "Lead / management" };

function salaryLabel(item: Opportunity) {
  if (!item.show_salary || (!item.salary_min && !item.salary_max)) return "Rémunération non publiée";
  const format = (value: string | null) => value ? Number(value).toLocaleString("fr-FR", { maximumFractionDigits: 0 }) : "";
  const periods: Record<string, string> = { hour: "/ heure", day: "/ jour", month: "/ mois", year: "/ an", project: "· forfait mission" };
  if (item.salary_min && item.salary_max) return `${format(item.salary_min)}–${format(item.salary_max)} ${item.salary_currency} ${periods[item.salary_period] || ""}`;
  return `${item.salary_min ? "Dès " : "Jusqu’à "}${format(item.salary_min || item.salary_max)} ${item.salary_currency} ${periods[item.salary_period] || ""}`;
}

export default function OpportunityDetailPage() {
  const params = useParams<{ slug: string }>();
  const router = useRouter();
  const { user, hydrated } = useAuth();
  const [item, setItem] = useState<Opportunity | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [coverLetter, setCoverLetter] = useState("");
  const [sharePortfolio, setSharePortfolio] = useState(true);
  const [resume, setResume] = useState<File | null>(null);
  const [screeningAnswers, setScreeningAnswers] = useState<string[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!params.slug) return;
    api.get<Opportunity>(`/opportunities/listings/${params.slug}/`)
      .then((data) => { setItem(data); setScreeningAnswers((data.screening_questions || []).map(() => "")); })
      .catch((e) => setError(e instanceof ApiError ? e.message : "Opportunité introuvable."))
      .finally(() => setLoading(false));
  }, [params.slug, user?.id]);

  async function apply() {
    if (!item) return;
    if (!hydrated || !user) {
      router.push(`/login?next=${encodeURIComponent(`/opportunities/${item.slug}`)}`);
      return;
    }
    if ((item.screening_questions || []).some((_, index) => !(screeningAnswers[index] || "").trim())) {
      setMessage("Répondez à toutes les questions de présélection avant d'envoyer votre candidature.");
      return;
    }
    setSubmitting(true); setMessage("");
    try {
      const fd = new FormData();
      fd.append("opportunity", String(item.id));
      fd.append("cover_letter", coverLetter);
      fd.append("screening_answers", JSON.stringify((item.screening_questions || []).map((question, index) => ({ question, answer: screeningAnswers[index] || "" }))));
      fd.append("share_portfolio", sharePortfolio ? "true" : "false");
      if (resume) fd.append("resume_file", resume);
      await api.post<OpportunityApplication>("/opportunities/applications/", fd);
      setMessage("Candidature envoyée. Votre profil professionnel a été figé pour cette candidature.");
      setItem({ ...item, already_applied: true });
    } catch (e) { setMessage(e instanceof ApiError ? e.message : "Impossible d'envoyer la candidature."); }
    finally { setSubmitting(false); }
  }

  if (loading) return <div className="container-app py-14 text-gray-500">Chargement...</div>;
  if (!item) return <div className="container-app py-14"><div className="card p-8 text-red-700">{error || "Opportunité indisponible."}</div></div>;
  const location = item.remote_worldwide ? "Monde entier" : [item.city, item.country].filter(Boolean).join(", ");

  return (
    <div className="container-app py-10">
      <Link href="/opportunities" className="mb-5 inline-flex items-center gap-2 text-sm font-semibold text-gray-500 hover:text-brand-700"><ArrowLeft size={15} /> Retour aux opportunités</Link>
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_360px]">
        <main className="card overflow-hidden">
          {item.cover_image && <div className="aspect-[16/6] w-full overflow-hidden bg-slate-100"><img loading="lazy" decoding="async" src={item.cover_image} alt="" className="h-full w-full object-cover" /></div>}
          <div className="p-6 sm:p-8">
          <div className="flex items-start gap-4">
            <div className="grid h-14 w-14 shrink-0 place-items-center overflow-hidden rounded-2xl bg-brand-50 text-brand-700">{item.employer.logo ? <img loading="lazy" decoding="async" src={item.employer.logo} alt="" className="h-full w-full object-contain p-0.5" /> : <BriefcaseBusiness size={25} />}</div>
            <div><div className="flex flex-wrap gap-2"><span className="badge bg-brand-50 text-brand-700">{labels[item.kind]}</span>{typeof item.match_score === "number" && <span className="badge bg-violet-50 text-violet-700">Compatibilité {item.match_score}%</span>}</div><h1 className="mt-2 text-2xl font-extrabold sm:text-3xl">{item.title}</h1><p className="mt-1 font-semibold text-gray-600">{item.employer.company_name}</p></div>
          </div>
          <div className="mt-5 flex flex-wrap gap-4 border-y border-gray-100 py-4 text-sm text-gray-600"><span className="flex items-center gap-1.5"><Radio size={15} /> {labels[item.work_mode]}</span>{location && <span className="flex items-center gap-1.5"><MapPin size={15} /> {location}</span>}<span>{labels[item.experience_level]}</span><span>{item.contract_type.replaceAll("_", " ")}</span>{item.department && <span>{item.department}</span>}{item.openings > 1 && <span>{item.openings} postes ouverts</span>}</div>
          <section className="mt-7"><h2 className="text-lg font-bold">À propos de l'opportunité</h2><p className="mt-3 whitespace-pre-line text-sm leading-7 text-gray-700">{item.description}</p></section>
          {item.responsibilities.length > 0 && <section className="mt-7"><h2 className="text-lg font-bold">Missions</h2><ul className="mt-3 space-y-2">{item.responsibilities.map((x) => <li key={x} className="flex gap-2 text-sm text-gray-700"><CheckCircle2 size={16} className="mt-0.5 shrink-0 text-brand-600" /> {x}</li>)}</ul></section>}
          {item.requirements.length > 0 && <section className="mt-7"><h2 className="text-lg font-bold">Profil recherché</h2><ul className="mt-3 space-y-2">{item.requirements.map((x) => <li key={x} className="flex gap-2 text-sm text-gray-700"><CheckCircle2 size={16} className="mt-0.5 shrink-0 text-brand-600" /> {x}</li>)}</ul></section>}
          <section className="mt-7"><h2 className="text-lg font-bold">Compétences</h2><div className="mt-3 flex flex-wrap gap-2">{item.skills_required.map((x) => <span key={x} className="rounded-full bg-brand-50 px-3 py-1.5 text-xs font-semibold text-brand-700">{x}</span>)}{item.skills_optional.map((x) => <span key={x} className="rounded-full bg-gray-100 px-3 py-1.5 text-xs font-medium text-gray-600">{x} · bonus</span>)}</div></section>
          <section className="mt-8 rounded-2xl bg-gray-50 p-5"><div className="flex items-start justify-between gap-3"><div><h2 className="font-bold">À propos de {item.employer.company_name}</h2><p className="mt-2 text-sm leading-6 text-gray-600">{item.employer.description || "Entreprise vérifiée sur KalanPro."}</p></div></div><div className="mt-3 flex flex-wrap gap-3">{item.employer.slug && <Link href={`/companies/${item.employer.slug}`} className="inline-flex items-center gap-1 text-sm font-semibold text-brand-700">Voir la page entreprise <ExternalLink size={13} /></Link>}{item.employer.website_url && <a href={item.employer.website_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm font-semibold text-brand-700">Site de l'entreprise <ExternalLink size={13} /></a>}</div></section>
          </div>
        </main>

        <aside className="space-y-4 lg:sticky lg:top-24 lg:self-start">
          <div className="card p-5">
            <div className="flex items-center gap-2 text-sm font-bold"><ShieldCheck size={17} className="text-brand-600" /> Candidature KalanPro</div>
            <p className="mt-2 text-xs leading-5 text-gray-500">Vos compétences, projets validés et certificats peuvent être joints comme preuves vérifiables. Le recruteur n'accède pas à vos données privées avant votre candidature.</p>
            <div className="mt-4 rounded-xl bg-gray-50 p-3"><p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400">Rémunération</p><p className="mt-1 text-sm font-bold text-ink">{salaryLabel(item)}</p></div>
            {item.application_deadline && <p className="mt-3 text-xs font-medium text-amber-700">Clôture : {new Date(item.application_deadline).toLocaleString("fr-FR")}</p>}
            {item.apply_mode === "external" ? <a href={item.external_application_url} target="_blank" rel="noreferrer" className="btn-primary mt-4 w-full">Candidater sur le site externe <ExternalLink size={15} /></a> : item.already_applied ? <div className="mt-4 rounded-xl bg-emerald-50 p-3 text-sm font-semibold text-emerald-700">Candidature déjà envoyée.</div> : (
              <div className="mt-4 space-y-3">
                <textarea value={coverLetter} onChange={(e) => setCoverLetter(e.target.value)} rows={5} placeholder="Message au recruteur (optionnel)" className="input-admin w-full" />
                {item.screening_questions?.map((question, index) => <label key={question} className="block text-xs font-semibold text-gray-600"><span>{question}</span><textarea required rows={3} value={screeningAnswers[index] || ""} onChange={(e) => setScreeningAnswers((rows) => rows.map((value, i) => i === index ? e.target.value : value))} className="input-admin mt-1 w-full" placeholder="Votre réponse" /></label>)}
                <label className="block text-xs font-semibold text-gray-600">CV spécifique (PDF/DOC/DOCX, optionnel)<input type="file" accept=".pdf,.doc,.docx" onChange={(e) => setResume(e.target.files?.[0] || null)} className="mt-1 block w-full text-xs" /></label>
                <label className="flex items-start gap-2 text-xs text-gray-600"><input type="checkbox" checked={sharePortfolio} onChange={(e) => setSharePortfolio(e.target.checked)} className="mt-0.5" /><span>Joindre mon portfolio et mes preuves KalanPro à cette candidature.</span></label>
                <button onClick={apply} disabled={submitting || !item.is_open} className="btn-primary w-full">{submitting ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />} Envoyer ma candidature</button>
              </div>
            )}
            {message && <div className={`mt-3 rounded-xl p-3 text-xs ${message.startsWith("Candidature") ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-800"}`}>{message}</div>}
          </div>
          <Link href="/dashboard/student/opportunities" className="btn-outline w-full">Optimiser mon profil candidat</Link>
        </aside>
      </div>
    </div>
  );
}
