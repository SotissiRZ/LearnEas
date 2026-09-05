"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BriefcaseBusiness, CheckCircle2, Download, ExternalLink, Loader2, Plus, Search, ShieldCheck, UserRoundSearch, X } from "lucide-react";
import { api, apiDownload, ApiError } from "@/lib/api";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import GuardScreen from "@/components/ui/GuardScreen";
import DashboardNav from "@/components/dashboard/DashboardNav";
import CountrySelect from "@/components/ui/CountrySelect";
import type { EmployerProfile, Opportunity, OpportunityApplication, Talent } from "@/types/opportunities";

type Paginated<T> = { count: number; next: string | null; previous: string | null; results: T[] };
const unwrap = <T,>(data: Paginated<T> | T[]) => Array.isArray(data) ? data : data.results;
const statuses = ["reviewing","shortlisted","interview","offer","hired","rejected"];
const statusLabel: Record<string,string> = { submitted:"Envoyée", reviewing:"En étude", shortlisted:"Présélectionné", interview:"Entretien", offer:"Offre", hired:"Retenu", rejected:"Non retenu", withdrawn:"Retirée" };
const initialOpportunity = { title:"", kind:"job", contract_type:"full_time", work_mode:"remote", experience_level:"entry", description:"", responsibilities:"", requirements:"", skills_required:"", skills_optional:"", country:"", city:"", remote_worldwide:true, salary_min:"", salary_max:"", salary_currency:"XOF", salary_period:"month", show_salary:true, apply_mode:"internal", external_application_url:"", application_deadline:"", status:"draft" };

export default function EmployerDashboardPage() {
  const { ready } = useAuthGuard({ roles: ["employer"], redirectTo: "/" });
  const [profile, setProfile] = useState<EmployerProfile>({ status:"none" });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [applications, setApplications] = useState<OpportunityApplication[]>([]);
  const [talents, setTalents] = useState<Talent[]>([]);
  const [talentSearch, setTalentSearch] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [jobForm, setJobForm] = useState({ ...initialOpportunity });
  const [logo, setLogo] = useState<File | null>(null);

  async function load() {
    setLoading(true); setError("");
    try {
      const p = await api.get<EmployerProfile>("/opportunities/employer-profile/"); setProfile(p);
      if (p.status === "approved") {
        const [jobs, apps, talentData] = await Promise.all([
          api.get<Paginated<Opportunity> | Opportunity[]>("/opportunities/listings/?mine=1&page_size=100&ordering=-created_at"),
          api.get<Paginated<OpportunityApplication> | OpportunityApplication[]>("/opportunities/applications/?recruiter=1&page_size=100&ordering=-applied_at"),
          api.get<Paginated<Talent> | Talent[]>("/opportunities/talents/?page_size=30"),
        ]);
        setOpportunities(unwrap(jobs)); setApplications(unwrap(apps)); setTalents(unwrap(talentData));
      }
    } catch (e) { setError(e instanceof ApiError ? e.message : "Impossible de charger l'espace recruteur."); }
    finally { setLoading(false); }
  }
  useEffect(() => { if (ready) void load(); }, [ready]);

  async function submitEmployer(e: React.FormEvent) {
    e.preventDefault(); setSaving(true); setError(""); setMessage("");
    try {
      const fd = new FormData();
      fd.append("company_name", profile.company_name || ""); fd.append("description", profile.description || ""); fd.append("industry", profile.industry || ""); fd.append("company_size", profile.company_size || ""); fd.append("website_url", profile.website_url || ""); fd.append("country", profile.country || ""); fd.append("city", profile.city || ""); if (logo) fd.append("logo", logo);
      const saved = profile.id ? await api.patch<EmployerProfile>(`/opportunities/employer-profile/${profile.id}/`, fd) : await api.post<EmployerProfile>("/opportunities/employer-profile/", fd);
      setProfile(saved); setLogo(null); setMessage(saved.status === "pending" ? "Demande recruteur envoyée à l'administration." : "Informations entreprise mises à jour.");
    } catch (e) { setError(e instanceof ApiError ? e.message : "Enregistrement impossible."); }
    finally { setSaving(false); }
  }

  async function createOpportunity(e: React.FormEvent) {
    e.preventDefault(); setSaving(true); setError("");
    try {
      const payload = {
        ...jobForm,
        salary_min: jobForm.salary_min || null,
        salary_max: jobForm.salary_max || null,
        application_deadline: jobForm.application_deadline ? new Date(jobForm.application_deadline).toISOString() : null,
        responsibilities: split(jobForm.responsibilities), requirements: split(jobForm.requirements), skills_required: split(jobForm.skills_required), skills_optional: split(jobForm.skills_optional),
        country: jobForm.remote_worldwide ? "" : jobForm.country,
      };
      await api.post("/opportunities/listings/", payload); setShowCreate(false); setJobForm({ ...initialOpportunity }); setMessage("Opportunité créée."); await load();
    } catch (e) { setError(e instanceof ApiError ? e.message : "Création impossible."); }
    finally { setSaving(false); }
  }

  async function updateJobStatus(job: Opportunity, status: string) {
    try { await api.patch(`/opportunities/listings/${job.slug}/`, { status }); setMessage(status === "published" ? "Opportunité publiée." : "Statut mis à jour."); await load(); }
    catch (e) { setError(e instanceof ApiError ? e.message : "Modification impossible."); }
  }

  async function review(app: OpportunityApplication, status: string) {
    const note = window.prompt("Note interne recruteur (optionnelle)", app.recruiter_note || "") ?? app.recruiter_note ?? "";
    try { await api.post(`/opportunities/applications/${app.id}/review/`, { status, recruiter_note: note }); await load(); }
    catch (e) { setError(e instanceof ApiError ? e.message : "Mise à jour impossible."); }
  }

  async function searchTalents() {
    try { const data = await api.get<Paginated<Talent> | Talent[]>(`/opportunities/talents/?page_size=50&search=${encodeURIComponent(talentSearch)}`); setTalents(unwrap(data)); }
    catch (e) { setError(e instanceof ApiError ? e.message : "Recherche impossible."); }
  }

  if (!ready) return <GuardScreen />;
  if (loading && profile.status === "none") return <div className="container-app py-10 text-gray-500">Chargement...</div>;

  return <div className="container-app py-10">
    <DashboardNav role="employer" />
    <div className="mb-8 flex flex-wrap items-end justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-widest text-brand-600">KalanPro Talent</p><h1 className="mt-1 text-2xl font-extrabold">Espace recruteur</h1><p className="mt-1 text-sm text-gray-500">Publiez des opportunités, évaluez des candidatures vérifiées et découvrez des talents.</p></div><div className="flex gap-2"><Link href="/opportunities" className="btn-outline"><ExternalLink size={14}/> Voir le marché</Link>{profile.status === "approved" && <button onClick={() => setShowCreate(true)} className="btn-primary"><Plus size={15}/> Nouvelle opportunité</button>}</div></div>
    {error && <div className="mb-5 rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</div>}{message && <div className="mb-5 rounded-xl bg-emerald-50 p-4 text-sm text-emerald-700">{message}</div>}

    {profile.status !== "approved" ? <EmployerApplication profile={profile} setProfile={setProfile} logo={logo} setLogo={setLogo} submit={submitEmployer} saving={saving} /> : <>
      <section className="mb-8 grid gap-4 sm:grid-cols-3"><Kpi label="Opportunités" value={opportunities.length}/><Kpi label="Candidatures" value={applications.length}/><Kpi label="Talents visibles" value={talents.length}/></section>
      <section className="card mb-8 overflow-hidden"><div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-100 p-5"><div><h2 className="font-bold">Mes opportunités</h2><p className="text-xs text-gray-500">Un contenu avec candidatures doit être clôturé ou archivé, pas supprimé.</p></div><button onClick={() => setShowCreate(true)} className="btn-primary !py-2 !text-xs"><Plus size={14}/> Publier</button></div><div className="overflow-x-auto"><table className="w-full min-w-[780px] text-sm"><thead className="table-head"><tr><th>Titre</th><th>Type</th><th>Lieu</th><th>Statut</th><th>Candidatures</th><th>Action</th></tr></thead><tbody className="divide-y divide-gray-100">{opportunities.map((job) => <tr key={job.id}><td className="px-4 py-3"><Link href={`/opportunities/${job.slug}`} className="font-semibold hover:text-brand-700">{job.title}</Link></td><td className="px-4 py-3">{job.kind}</td><td className="px-4 py-3">{job.remote_worldwide ? "Monde entier" : [job.city,job.country].filter(Boolean).join(", ")}</td><td className="px-4 py-3"><span className="badge bg-gray-100 text-gray-700">{job.status}</span></td><td className="px-4 py-3">{job.applications_count || 0}</td><td className="px-4 py-3"><select value={job.status} onChange={(e) => updateJobStatus(job,e.target.value)} className="rounded-lg border border-gray-200 px-2 py-1 text-xs"><option value="draft">Brouillon</option><option value="published">Publiée</option><option value="closed">Clôturée</option><option value="archived">Archivée</option></select></td></tr>)}</tbody></table></div></section>
      <section className="card mb-8 overflow-hidden"><div className="border-b border-gray-100 p-5"><h2 className="font-bold">Candidatures reçues</h2><p className="mt-1 text-xs text-gray-500">Les preuves affichées sont des snapshots pris au moment de la candidature.</p></div>{applications.length === 0 ? <div className="p-8 text-center text-gray-500">Aucune candidature.</div> : <div className="divide-y divide-gray-100">{applications.map((app) => <div key={app.id} className="p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><h3 className="font-bold">{app.candidate_name_snapshot}</h3><p className="text-xs text-gray-500">{app.headline_snapshot || app.country_snapshot} · {app.candidate_email_snapshot}</p><p className="mt-1 text-xs font-semibold text-violet-700">Match {app.match_score}% · {app.opportunity_title}</p></div><select value={app.status} onChange={(e) => review(app,e.target.value)} className="input-admin !w-auto !py-1.5 text-xs"><option value="submitted">Envoyée</option>{statuses.map((s) => <option key={s} value={s}>{statusLabel[s]}</option>)}</select></div>{app.cover_letter && <p className="mt-3 rounded-xl bg-gray-50 p-3 text-sm text-gray-600">{app.cover_letter}</p>}<div className="mt-3 flex flex-wrap gap-2">{app.skills_snapshot.slice(0,10).map((s) => <span key={s} className="rounded-full bg-brand-50 px-2 py-1 text-[11px] font-semibold text-brand-700">{s}</span>)}</div><div className="mt-3 flex flex-wrap gap-2 text-xs">{app.resume_url && <button onClick={() => apiDownload(app.resume_url!, `CV-${app.candidate_name_snapshot}`)} className="btn-outline !py-1.5 !text-xs"><Download size={13}/> CV</button>}{app.portfolio_snapshot?.slug && <Link href={`/portfolio/${app.portfolio_snapshot.slug}`} className="btn-outline !py-1.5 !text-xs">Portfolio</Link>}{app.certificates_snapshot.slice(0,3).map((c) => <Link key={c.number} href={`/certificates/verify/${c.verification_code}`} className="btn-outline !py-1.5 !text-xs"><ShieldCheck size={13}/> {c.title}</Link>)}</div></div>)}</div>}</section>
      <section className="card p-5"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="flex items-center gap-2 font-bold"><UserRoundSearch size={18}/> Vivier de talents</h2><p className="mt-1 text-xs text-gray-500">Uniquement les candidats ayant activé volontairement la visibilité recruteur.</p></div><div className="flex gap-2"><input value={talentSearch} onChange={(e) => setTalentSearch(e.target.value)} onKeyDown={(e) => { if(e.key === "Enter") void searchTalents(); }} className="input-admin" placeholder="Excel, marketing, développeur..."/><button onClick={searchTalents} className="btn-outline"><Search size={14}/></button></div></div><div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-3">{talents.map((t) => <div key={t.id} className="rounded-2xl border border-gray-100 p-4"><h3 className="font-bold">{t.full_name}</h3><p className="mt-1 text-xs text-gray-500">{t.headline || "Talent KalanPro"} · {t.country}</p><div className="mt-3 flex flex-wrap gap-1">{t.skills.slice(0,6).map((s) => <span key={s} className="rounded-full bg-gray-100 px-2 py-1 text-[10px]">{s}</span>)}</div>{t.portfolio_slug && <Link href={`/portfolio/${t.portfolio_slug}`} className="mt-3 inline-block text-xs font-semibold text-brand-700">Voir le portfolio →</Link>}</div>)}</div></section>
    </>}

    {showCreate && <OpportunityModal form={jobForm} setForm={setJobForm} onClose={() => setShowCreate(false)} onSubmit={createOpportunity} saving={saving}/>} 
  </div>;
}

function EmployerApplication({profile,setProfile,logo,setLogo,submit,saving}:{profile:EmployerProfile;setProfile:(p:EmployerProfile)=>void;logo:File|null;setLogo:(f:File|null)=>void;submit:(e:React.FormEvent)=>void;saving:boolean}) {
  return <form onSubmit={submit} className="card max-w-4xl p-6"><div className="mb-5"><h2 className="text-lg font-bold">{profile.status === "none" ? "Créer un espace entreprise" : profile.status === "pending" ? "Demande en cours de validation" : "Mettre à jour et renvoyer la demande"}</h2><p className="mt-1 text-sm text-gray-500">Les entreprises sont vérifiées avant de pouvoir publier ou consulter le vivier de talents.</p>{profile.status !== "none" && <div className={`mt-3 rounded-xl p-3 text-sm ${profile.status === "pending" ? "bg-amber-50 text-amber-800" : "bg-red-50 text-red-700"}`}>Statut : <strong>{profile.status}</strong>{profile.review_note ? ` · ${profile.review_note}` : ""}</div>}</div><div className="grid gap-4 md:grid-cols-2"><Field label="Nom de l'entreprise"><input required value={profile.company_name || ""} onChange={(e) => setProfile({...profile,company_name:e.target.value})} className="input-admin w-full"/></Field><Field label="Secteur"><input value={profile.industry || ""} onChange={(e) => setProfile({...profile,industry:e.target.value})} className="input-admin w-full" placeholder="EdTech, Finance, ONG..."/></Field><Field label="Pays"><CountrySelect required value={profile.country || ""} onChange={(v) => setProfile({...profile,country:v})}/></Field><Field label="Ville"><input value={profile.city || ""} onChange={(e) => setProfile({...profile,city:e.target.value})} className="input-admin w-full"/></Field><Field label="Taille"><select value={profile.company_size || ""} onChange={(e) => setProfile({...profile,company_size:e.target.value})} className="input-admin w-full"><option value="">Non précisé</option><option value="solo">Indépendant</option><option value="1-10">1–10</option><option value="11-50">11–50</option><option value="51-200">51–200</option><option value="201-1000">201–1000</option><option value="1000+">1000+</option></select></Field><Field label="Site web"><input type="url" value={profile.website_url || ""} onChange={(e) => setProfile({...profile,website_url:e.target.value})} className="input-admin w-full" placeholder="https://..."/></Field><Field label="Présentation" wide><textarea required rows={5} value={profile.description || ""} onChange={(e) => setProfile({...profile,description:e.target.value})} className="input-admin w-full"/></Field><Field label="Logo" wide><input type="file" accept="image/*" onChange={(e) => setLogo(e.target.files?.[0] || null)} className="block w-full text-xs"/>{logo && <p className="mt-1 text-xs text-gray-500">{logo.name}</p>}</Field></div><button disabled={saving || profile.status === "suspended"} className="btn-primary mt-5">{saving ? <Loader2 size={15} className="animate-spin"/> : <CheckCircle2 size={15}/>} {profile.status === "none" ? "Envoyer pour validation" : profile.status === "pending" ? "Mettre à jour ma demande" : profile.status === "suspended" ? "Compte suspendu" : "Corriger et renvoyer"}</button></form>;
}

function OpportunityModal({form,setForm,onClose,onSubmit,saving}:{form:any;setForm:(x:any)=>void;onClose:()=>void;onSubmit:(e:React.FormEvent)=>void;saving:boolean}) { return <div className="fixed inset-0 z-[90] grid place-items-center bg-black/50 p-4"><form onSubmit={onSubmit} className="card max-h-[92vh] w-full max-w-4xl overflow-y-auto p-6"><div className="flex items-center justify-between"><div><h2 className="text-lg font-bold">Nouvelle opportunité</h2><p className="text-xs text-gray-500">Vous pouvez enregistrer un brouillon avant publication.</p></div><button type="button" onClick={onClose} className="rounded-lg p-2 hover:bg-gray-100"><X size={18}/></button></div><div className="mt-5 grid gap-4 md:grid-cols-2"><Field label="Titre"><input required value={form.title} onChange={(e)=>setForm({...form,title:e.target.value})} className="input-admin w-full"/></Field><Field label="Type"><select value={form.kind} onChange={(e)=>setForm({...form,kind:e.target.value})} className="input-admin w-full"><option value="job">Emploi</option><option value="internship">Stage</option><option value="freelance">Freelance</option><option value="mission">Mission</option></select></Field><Field label="Contrat"><select value={form.contract_type} onChange={(e)=>setForm({...form,contract_type:e.target.value})} className="input-admin w-full"><option value="full_time">Temps plein</option><option value="part_time">Temps partiel</option><option value="permanent">CDI</option><option value="fixed_term">CDD</option><option value="internship">Stage</option><option value="freelance">Freelance</option><option value="project">Projet / mission</option></select></Field><Field label="Mode"><select value={form.work_mode} onChange={(e)=>setForm({...form,work_mode:e.target.value})} className="input-admin w-full"><option value="remote">À distance</option><option value="hybrid">Hybride</option><option value="onsite">Sur site</option></select></Field><Field label="Niveau"><select value={form.experience_level} onChange={(e)=>setForm({...form,experience_level:e.target.value})} className="input-admin w-full"><option value="entry">Premier emploi</option><option value="junior">Junior</option><option value="mid">Intermédiaire</option><option value="senior">Senior</option><option value="lead">Lead / management</option></select></Field><Field label="Candidature"><select value={form.apply_mode} onChange={(e)=>setForm({...form,apply_mode:e.target.value})} className="input-admin w-full"><option value="internal">Dans KalanPro</option><option value="external">Lien externe</option></select></Field>{form.apply_mode === "external" && <Field label="Lien externe"><input type="url" required value={form.external_application_url} onChange={(e)=>setForm({...form,external_application_url:e.target.value})} className="input-admin w-full"/></Field>}<Field label="Description" wide><textarea required rows={6} value={form.description} onChange={(e)=>setForm({...form,description:e.target.value})} className="input-admin w-full"/></Field><Field label="Missions (séparées par ;)"><textarea rows={4} value={form.responsibilities} onChange={(e)=>setForm({...form,responsibilities:e.target.value})} className="input-admin w-full"/></Field><Field label="Exigences (séparées par ;)"><textarea rows={4} value={form.requirements} onChange={(e)=>setForm({...form,requirements:e.target.value})} className="input-admin w-full"/></Field><Field label="Compétences requises"><input value={form.skills_required} onChange={(e)=>setForm({...form,skills_required:e.target.value})} className="input-admin w-full" placeholder="Excel, Power BI, SQL"/></Field><Field label="Compétences bonus"><input value={form.skills_optional} onChange={(e)=>setForm({...form,skills_optional:e.target.value})} className="input-admin w-full"/></Field><div className="md:col-span-2"><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.remote_worldwide} onChange={(e)=>setForm({...form,remote_worldwide:e.target.checked})}/><span>Ouvert au télétravail depuis n'importe quel pays</span></label></div>{!form.remote_worldwide && <><Field label="Pays"><CountrySelect value={form.country} onChange={(v)=>setForm({...form,country:v})}/></Field><Field label="Ville"><input value={form.city} onChange={(e)=>setForm({...form,city:e.target.value})} className="input-admin w-full"/></Field></>}<Field label="Rémunération min"><input type="number" min="0" value={form.salary_min} onChange={(e)=>setForm({...form,salary_min:e.target.value})} className="input-admin w-full"/></Field><Field label="Rémunération max"><input type="number" min="0" value={form.salary_max} onChange={(e)=>setForm({...form,salary_max:e.target.value})} className="input-admin w-full"/></Field><Field label="Devise"><select value={form.salary_currency} onChange={(e)=>setForm({...form,salary_currency:e.target.value})} className="input-admin w-full"><option>XOF</option><option>XAF</option><option>EUR</option><option>MAD</option><option>USD</option></select></Field><Field label="Période"><select value={form.salary_period} onChange={(e)=>setForm({...form,salary_period:e.target.value})} className="input-admin w-full"><option value="month">Par mois</option><option value="year">Par an</option><option value="day">Par jour</option><option value="hour">Par heure</option><option value="project">Forfait mission</option></select></Field><Field label="Clôture des candidatures"><input type="datetime-local" value={form.application_deadline} onChange={(e)=>setForm({...form,application_deadline:e.target.value})} className="input-admin w-full"/></Field><Field label="Statut"><select value={form.status} onChange={(e)=>setForm({...form,status:e.target.value})} className="input-admin w-full"><option value="draft">Brouillon</option><option value="published">Publier immédiatement</option></select></Field></div><div className="mt-5 flex justify-end gap-2"><button type="button" onClick={onClose} className="btn-outline">Annuler</button><button disabled={saving} className="btn-primary">{saving ? <Loader2 size={15} className="animate-spin"/> : <BriefcaseBusiness size={15}/>} Enregistrer</button></div></form></div>; }
function Field({label,children,wide=false}:{label:string;children:React.ReactNode;wide?:boolean}) { return <label className={wide?"md:col-span-2":""}><span className="mb-1 block text-xs font-semibold text-gray-600">{label}</span>{children}</label>; }
function Kpi({label,value}:{label:string;value:number}) { return <div className="card p-5"><p className="text-2xl font-extrabold">{value}</p><p className="mt-1 text-xs text-gray-500">{label}</p></div>; }
function split(value:string){return value.split(/[;,\n]/).map((x)=>x.trim()).filter(Boolean)}
