"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BriefcaseBusiness, CalendarClock, CheckCircle2, Download, Eye, Loader2, Search, Sparkles, UserRoundSearch } from "lucide-react";
import DashboardNav from "@/components/dashboard/DashboardNav";
import GuardScreen from "@/components/ui/GuardScreen";
import CountryMultiSelect from "@/components/ui/CountryMultiSelect";
import OpportunityCard from "@/components/opportunities/OpportunityCard";
import { api, apiDownload, ApiError } from "@/lib/api";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import type { CandidateProfile, EmploymentOffer, Opportunity, OpportunityApplication, RecruitmentInterview, TalentAccessLog } from "@/types/opportunities";

type Paginated<T> = { count: number; next: string | null; previous: string | null; results: T[] };
const statusLabel: Record<string, string> = { submitted: "Envoyée", reviewing: "En étude", shortlisted: "Présélectionné", interview: "Entretien", offer: "Offre", hired: "Retenu", rejected: "Non retenu", withdrawn: "Retirée" };
const statusClass: Record<string, string> = { submitted: "bg-slate-100 text-slate-700", reviewing: "bg-blue-50 text-blue-700", shortlisted: "bg-violet-50 text-violet-700", interview: "bg-amber-50 text-amber-700", offer: "bg-emerald-50 text-emerald-700", hired: "bg-emerald-100 text-emerald-800", rejected: "bg-red-50 text-red-700", withdrawn: "bg-gray-100 text-gray-500" };

function splitList(value: string) { return value.split(",").map((x) => x.trim()).filter(Boolean); }

export default function StudentOpportunitiesPage() {
  const { ready } = useAuthGuard();
  const [profile, setProfile] = useState<CandidateProfile | null>(null);
  const [matches, setMatches] = useState<Opportunity[]>([]);
  const [applications, setApplications] = useState<OpportunityApplication[]>([]);
  const [accessLogs, setAccessLogs] = useState<TalentAccessLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [resume, setResume] = useState<File | null>(null);
  const [skillsText, setSkillsText] = useState("");
  const [rolesText, setRolesText] = useState("");

  async function load() {
    setLoading(true); setError("");
    try {
      const [p, m, a, accesses] = await Promise.all([
        api.get<CandidateProfile>("/opportunities/candidate-profile/"),
        api.get<Opportunity[]>("/opportunities/listings/matches/"),
        api.get<Paginated<OpportunityApplication> | OpportunityApplication[]>("/opportunities/applications/?page_size=100&ordering=-applied_at"),
        api.get<TalentAccessLog[]>("/opportunities/candidate-profile/talent-accesses/").catch(() => []),
      ]);
      setProfile(p); setSkillsText((p.skills || []).join(", ")); setRolesText((p.desired_roles || []).join(", "));
      setMatches(m); setApplications(Array.isArray(a) ? a : a.results); setAccessLogs(accesses);
    } catch (e) { setError(e instanceof ApiError ? e.message : "Impossible de charger votre espace opportunités."); }
    finally { setLoading(false); }
  }

  useEffect(() => { if (ready) void load(); }, [ready]);

  async function saveProfile() {
    if (!profile) return;
    setSaving(true); setMessage(""); setError("");
    try {
      const fd = new FormData();
      fd.append("headline", profile.headline || "");
      fd.append("summary", profile.summary || "");
      fd.append("skills", JSON.stringify(splitList(skillsText)));
      fd.append("desired_roles", JSON.stringify(splitList(rolesText)));
      profile.preferred_kinds.forEach(() => {});
      fd.append("preferred_kinds", JSON.stringify(profile.preferred_kinds || []));
      fd.append("preferred_work_modes", JSON.stringify(profile.preferred_work_modes || []));
      fd.append("preferred_countries", JSON.stringify(profile.preferred_countries || []));
      fd.append("minimum_salary", profile.minimum_salary || "");
      fd.append("salary_currency", profile.salary_currency || "EUR");
      fd.append("availability", profile.availability || "open");
      fd.append("years_experience", String(profile.years_experience || 0));
      fd.append("is_searchable", profile.is_searchable ? "true" : "false");
      if (resume) fd.append("resume", resume);
      const saved = await api.patch<CandidateProfile>("/opportunities/candidate-profile/me/", fd);
      setProfile(saved); setSkillsText(saved.skills.join(", ")); setRolesText(saved.desired_roles.join(", ")); setResume(null);
      setMessage("Profil candidat mis à jour. Le matching a été recalculé.");
      const updated = await api.get<Opportunity[]>("/opportunities/listings/matches/"); setMatches(updated);
    } catch (e) { setError(e instanceof ApiError ? e.message : "Impossible d'enregistrer le profil."); }
    finally { setSaving(false); }
  }

  async function withdraw(id: number) {
    if (!window.confirm("Retirer cette candidature ?")) return;
    try { await api.post(`/opportunities/applications/${id}/withdraw/`, {}); await load(); }
    catch (e) { setError(e instanceof ApiError ? e.message : "Retrait impossible."); }
  }

  if (!ready) return <GuardScreen />;
  if (loading && !profile) return <div className="container-app py-10"><DashboardNav role="student" /><p className="text-gray-500">Chargement...</p></div>;

  return (
    <div className="container-app py-10">
      <DashboardNav role="student" />
      <div className="mb-7 flex flex-wrap items-end justify-between gap-3"><div><h1 className="text-2xl font-extrabold">Emploi & missions</h1><p className="mt-1 text-sm text-gray-500">Préparez votre profil, découvrez les meilleurs matchs et suivez vos candidatures.</p></div><Link href="/opportunities" className="btn-outline"><Search size={15} /> Explorer toutes les opportunités</Link></div>
      {error && <div className="mb-5 rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</div>}
      {message && <div className="mb-5 rounded-xl bg-emerald-50 p-4 text-sm text-emerald-700">{message}</div>}

      {profile && <section className="card mb-8 p-5 sm:p-6">
        <div className="mb-5 flex items-start justify-between gap-3"><div><h2 className="flex items-center gap-2 text-lg font-bold"><UserRoundSearch size={19} /> Profil candidat</h2><p className="mt-1 text-xs text-gray-500">Ce profil est utilisé pour calculer vos recommandations. Le CV reste privé et n'est remis qu'aux recruteurs concernés.</p></div>{profile.portfolio_slug && <Link href={`/portfolio/${profile.portfolio_slug}`} className="text-xs font-semibold text-brand-700">Voir mon portfolio</Link>}</div>
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="Titre professionnel"><input value={profile.headline || ""} onChange={(e) => setProfile({ ...profile, headline: e.target.value })} className="input-admin w-full" placeholder="Ex. Analyste Excel / Power BI" /></Field>
          <Field label="Années d'expérience"><input type="number" min="0" max="80" value={profile.years_experience || 0} onChange={(e) => setProfile({ ...profile, years_experience: Number(e.target.value) || 0 })} className="input-admin w-full" /></Field>
          <Field label="Compétences (séparées par des virgules)"><input value={skillsText} onChange={(e) => setSkillsText(e.target.value)} className="input-admin w-full" placeholder="Excel, Power BI, SQL, Canva..." /></Field>
          <Field label="Métiers recherchés"><input value={rolesText} onChange={(e) => setRolesText(e.target.value)} className="input-admin w-full" placeholder="Data analyst, Assistant comptable..." /></Field>
          <Field label="Disponibilité"><select value={profile.availability} onChange={(e) => setProfile({ ...profile, availability: e.target.value })} className="input-admin w-full"><option value="immediate">Disponible immédiatement</option><option value="2_weeks">Sous 2 semaines</option><option value="1_month">Sous 1 mois</option><option value="open">À l'écoute</option><option value="unavailable">Indisponible</option></select></Field>
          <Field label="Rémunération minimale souhaitée"><div className="grid grid-cols-[1fr_100px] gap-2"><input type="number" min="0" value={profile.minimum_salary || ""} onChange={(e) => setProfile({ ...profile, minimum_salary: e.target.value || null })} className="input-admin w-full" /><select value={profile.salary_currency || "EUR"} onChange={(e) => setProfile({ ...profile, salary_currency: e.target.value })} className="input-admin w-full"><option>EUR</option><option>XOF</option><option>XAF</option><option>MAD</option><option>USD</option></select></div></Field>
          <Field label="Types d'opportunités"><CheckGroup values={profile.preferred_kinds} onChange={(v) => setProfile({ ...profile, preferred_kinds: v })} options={[["job","Emploi"],["internship","Stage"],["freelance","Freelance"],["mission","Mission"]]} /></Field>
          <Field label="Modes de travail"><CheckGroup values={profile.preferred_work_modes} onChange={(v) => setProfile({ ...profile, preferred_work_modes: v })} options={[["remote","À distance"],["hybrid","Hybride"],["onsite","Sur site"]]} /></Field>
          <Field label="Pays souhaités"><CountryMultiSelect value={profile.preferred_countries || []} onChange={(v) => setProfile({ ...profile, preferred_countries: v })} /></Field>
          <Field label="CV"><div className="space-y-2"><input type="file" accept=".pdf,.doc,.docx" onChange={(e) => setResume(e.target.files?.[0] || null)} className="block w-full text-xs" />{profile.resume_url && <button type="button" onClick={() => apiDownload(profile.resume_url!, "cv")} className="btn-outline !py-1.5 !text-xs"><Download size={13} /> Télécharger le CV actuel</button>}</div></Field>
          <Field label="Présentation" wide><textarea rows={5} value={profile.summary || ""} onChange={(e) => setProfile({ ...profile, summary: e.target.value })} className="input-admin w-full" placeholder="Votre parcours, vos forces et ce que vous recherchez." /></Field>
          <div className="md:col-span-2 flex flex-wrap items-center justify-between gap-3 rounded-xl bg-gray-50 p-4"><label className="flex items-start gap-2 text-sm"><input type="checkbox" checked={profile.is_searchable} onChange={(e) => setProfile({ ...profile, is_searchable: e.target.checked })} className="mt-0.5" /><span><strong>Visible dans le vivier de talents KalanPro</strong><br/><span className="text-xs text-gray-500">Les recruteurs approuvés voient uniquement vos informations professionnelles publiques, jamais votre email ou téléphone.</span></span></label><button onClick={saveProfile} disabled={saving} className="btn-primary">{saving ? <Loader2 size={16} className="animate-spin" /> : <CheckCircle2 size={16} />} Enregistrer</button></div>
        </div>
      </section>}

      <section className="mb-9"><div className="mb-4 flex items-center justify-between"><div><h2 className="flex items-center gap-2 text-xl font-bold"><Sparkles size={18} className="text-violet-600" /> Meilleurs matchs</h2><p className="mt-1 text-xs text-gray-500">Score calculé à partir de vos compétences, préférences et preuves KalanPro.</p></div></div>{matches.length ? <div className="catalog-grid">{matches.slice(0, 9).map((m) => <OpportunityCard key={m.id} opportunity={m} />)}</div> : <div className="card p-8 text-center text-gray-500">Complétez votre profil pour améliorer les recommandations.</div>}</section>

      <section><h2 className="mb-4 flex items-center gap-2 text-xl font-bold"><BriefcaseBusiness size={18} /> Mes candidatures</h2>{applications.length === 0 ? <div className="card p-8 text-center text-gray-500">Aucune candidature pour le moment.</div> : <div className="space-y-3">{applications.map((app) => <div key={app.id} className="card p-4"><div className="flex flex-col gap-3 sm:flex-row sm:items-center"><div className="min-w-0 flex-1"><Link href={`/opportunities/${app.opportunity_slug}`} className="font-bold hover:text-brand-700">{app.opportunity_title}</Link><p className="mt-1 text-xs text-gray-500">{app.company_name} · candidature du {new Date(app.applied_at).toLocaleDateString("fr-FR")} · match {app.match_score}%</p></div><span className={`badge ${statusClass[app.status] || "bg-gray-100 text-gray-600"}`}>{statusLabel[app.status] || app.status}</span>{!["hired","rejected","withdrawn"].includes(app.status) && <button onClick={() => withdraw(app.id)} className="text-xs font-semibold text-red-600">Retirer</button>}</div><ApplicationProcess application={app} onChanged={load} /></div>)}</div>}</section>

      <section className="mt-9"><h2 className="mb-2 flex items-center gap-2 text-xl font-bold"><Eye size={18} /> Journal d’accès recruteur</h2><p className="mb-4 text-xs text-gray-500">Vous voyez quelles entreprises ont consulté votre profil, ajouté votre profil aux favoris ou ouvert votre candidature.</p>{accessLogs.length === 0 ? <div className="card p-6 text-sm text-gray-500">Aucun accès recruteur enregistré.</div> : <div className="card divide-y divide-gray-100">{accessLogs.slice(0, 30).map((row) => <div key={row.id} className="flex flex-wrap items-center justify-between gap-2 p-4 text-sm"><div><strong>{row.company_name}</strong><p className="mt-0.5 text-xs text-gray-500">{row.access_type === "bookmark" ? "Ajout aux favoris" : row.access_type === "application" ? "Consultation de candidature" : "Consultation du profil"}</p></div><time className="text-xs text-gray-400">{new Date(row.created_at).toLocaleString("fr-FR")}</time></div>)}</div>}</section>
    </div>
  );
}

function ApplicationProcess({ application, onChanged }: { application: OpportunityApplication; onChanged: () => Promise<void> }) {
  const [interviews, setInterviews] = useState<RecruitmentInterview[]>([]);
  const [offer, setOffer] = useState<EmploymentOffer | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    const needsInterviews = ["interview", "offer", "hired", "rejected"].includes(application.status);
    const needsOffer = ["offer", "hired", "rejected"].includes(application.status);
    if (!needsInterviews && !needsOffer) {
      setInterviews([]); setOffer(null);
      return () => { active = false; };
    }
    Promise.all([
      needsInterviews
        ? api.get<RecruitmentInterview[]>(`/opportunities/applications/${application.id}/interviews/`).catch(() => [])
        : Promise.resolve([] as RecruitmentInterview[]),
      needsOffer
        ? api.get<EmploymentOffer>(`/opportunities/applications/${application.id}/offer/`).catch(() => null)
        : Promise.resolve(null),
    ]).then(([rows, currentOffer]) => { if (active) { setInterviews(rows); setOffer(currentOffer); } });
    return () => { active = false; };
  }, [application.id, application.status]);

  async function respond(decision: "accepted" | "declined") {
    if (!window.confirm(decision === "accepted" ? "Accepter cette offre d’embauche ?" : "Refuser cette offre d’embauche ?")) return;
    setBusy(true); setError("");
    try {
      const updated = await api.post<EmploymentOffer>(`/opportunities/applications/${application.id}/offer-response/`, { decision });
      setOffer(updated);
      await onChanged();
    } catch (e) { setError(e instanceof ApiError ? e.message : "Réponse à l’offre impossible."); }
    finally { setBusy(false); }
  }

  if (!interviews.length && !offer) return null;
  return <div className="mt-4 space-y-3 border-t border-gray-100 pt-4">
    {interviews.length > 0 && <div className="rounded-xl bg-amber-50 p-3"><p className="flex items-center gap-2 text-xs font-bold text-amber-800"><CalendarClock size={14}/> Entretien</p>{interviews.map((row) => <div key={row.id} className="mt-2 text-xs leading-5 text-amber-900"><strong>{new Date(row.scheduled_at).toLocaleString("fr-FR")}</strong> · {row.duration_minutes} min · {row.mode}{row.location_or_url && <div className="break-all">{row.location_or_url}</div>}{row.candidate_message && <div className="mt-1">{row.candidate_message}</div>}</div>)}</div>}
    {offer && <div className="rounded-xl border border-emerald-100 bg-emerald-50 p-3"><div className="flex flex-wrap items-start justify-between gap-2"><div><p className="text-xs font-bold text-emerald-800">Offre d’embauche</p><p className="mt-1 text-sm font-semibold text-emerald-950">{offer.title}</p>{offer.message && <p className="mt-1 text-xs leading-5 text-emerald-900">{offer.message}</p>}{offer.salary_amount && <p className="mt-2 text-xs font-semibold text-emerald-900">{offer.salary_amount} {offer.salary_currency}</p>}</div><span className="rounded-full bg-white px-2 py-1 text-[10px] font-bold uppercase text-emerald-700">{offer.status}</span></div>{offer.status === "pending" && <div className="mt-3 flex gap-2"><button disabled={busy} onClick={() => void respond("accepted")} className="btn-primary !py-1.5 !text-xs">Accepter</button><button disabled={busy} onClick={() => void respond("declined")} className="btn-outline !py-1.5 !text-xs">Refuser</button></div>}{error && <p className="mt-2 text-xs text-red-600">{error}</p>}</div>}
  </div>;
}

function Field({ label, children, wide = false }: { label: string; children: React.ReactNode; wide?: boolean }) { return <label className={wide ? "md:col-span-2" : ""}><span className="mb-1 block text-xs font-semibold text-gray-600">{label}</span>{children}</label>; }
function CheckGroup({ values, onChange, options }: { values: string[]; onChange: (v: string[]) => void; options: string[][] }) { const set = new Set(values || []); return <div className="flex flex-wrap gap-2">{options.map(([value,label]) => <label key={value} className={`cursor-pointer rounded-full border px-3 py-1.5 text-xs ${set.has(value) ? "border-brand-300 bg-brand-50 text-brand-700" : "border-gray-200 text-gray-600"}`}><input type="checkbox" className="sr-only" checked={set.has(value)} onChange={(e) => onChange(e.target.checked ? [...values, value] : values.filter((x) => x !== value))} />{label}</label>)}</div>; }
