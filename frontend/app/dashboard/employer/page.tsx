"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  BarChart3, BriefcaseBusiness, Building2, CalendarClock, CheckCircle2, ChevronRight, Download,
  ExternalLink, Eye, FilePenLine, ImagePlus, LayoutDashboard, Loader2, MapPin, Plus, Search,
  ShieldCheck, Sparkles, Star, Tags, UserCheck, UserRoundSearch, UsersRound, X,
} from "lucide-react";
import { api, apiDownload, ApiError } from "@/lib/api";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import GuardScreen from "@/components/ui/GuardScreen";
import DashboardNav from "@/components/dashboard/DashboardNav";
import CountrySelect from "@/components/ui/CountrySelect";
import type {
  EmployerAnalytics, EmployerProfile, Opportunity, OpportunityApplication, Talent, TalentBookmark,
} from "@/types/opportunities";

type Paginated<T> = { count: number; next: string | null; previous: string | null; results: T[] };
type Tab = "overview" | "jobs" | "candidates" | "talents" | "brand";
const unwrap = <T,>(data: Paginated<T> | T[]) => Array.isArray(data) ? data : data.results;
const pipelineStatuses = ["submitted", "reviewing", "shortlisted", "interview", "offer", "hired", "rejected"];
const statusLabel: Record<string, string> = {
  submitted: "Nouvelles", reviewing: "En étude", shortlisted: "Présélection", interview: "Entretien",
  offer: "Offre", hired: "Recruté", rejected: "Non retenu", withdrawn: "Retirée",
};
const statusTone: Record<string, string> = {
  submitted: "bg-slate-100 text-slate-700", reviewing: "bg-blue-50 text-blue-700", shortlisted: "bg-violet-50 text-violet-700",
  interview: "bg-amber-50 text-amber-800", offer: "bg-cyan-50 text-cyan-700", hired: "bg-emerald-50 text-emerald-700", rejected: "bg-red-50 text-red-700",
};
const initialOpportunity = {
  title: "", kind: "job", contract_type: "full_time", work_mode: "remote", experience_level: "entry", description: "",
  department: "", openings: "1", responsibilities: "", requirements: "", skills_required: "", skills_optional: "",
  screening_questions: "", country: "", city: "", remote_worldwide: true, salary_min: "", salary_max: "", salary_currency: "XOF",
  salary_period: "month", show_salary: true, apply_mode: "internal", external_application_url: "", application_deadline: "", status: "draft",
};

export default function EmployerDashboardPage() {
  const { ready } = useAuthGuard({ roles: ["employer"], redirectTo: "/" });
  const [tab, setTab] = useState<Tab>("overview");
  const [profile, setProfile] = useState<EmployerProfile>({ status: "none" });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [applications, setApplications] = useState<OpportunityApplication[]>([]);
  const [talents, setTalents] = useState<Talent[]>([]);
  const [bookmarks, setBookmarks] = useState<TalentBookmark[]>([]);
  const [analytics, setAnalytics] = useState<EmployerAnalytics | null>(null);
  const [talentSearch, setTalentSearch] = useState("");
  const [talentCountry, setTalentCountry] = useState("");
  const [talentAvailability, setTalentAvailability] = useState("");
  const [talentExperience, setTalentExperience] = useState("");
  const [candidateSearch, setCandidateSearch] = useState("");
  const [candidateJob, setCandidateJob] = useState("");
  const [selectedApp, setSelectedApp] = useState<OpportunityApplication | null>(null);
  const [showJobModal, setShowJobModal] = useState(false);
  const [editingJob, setEditingJob] = useState<Opportunity | null>(null);
  const [jobForm, setJobForm] = useState({ ...initialOpportunity });
  const [jobCover, setJobCover] = useState<File | null>(null);
  const [logo, setLogo] = useState<File | null>(null);
  const [banner, setBanner] = useState<File | null>(null);

  async function load() {
    setLoading(true); setError("");
    try {
      const p = await api.get<EmployerProfile>("/opportunities/employer-profile/");
      setProfile(p);
      if (p.status === "approved") {
        const [jobs, apps, talentData, saved, stats] = await Promise.allSettled([
          api.get<Paginated<Opportunity> | Opportunity[]>("/opportunities/listings/?mine=1&page_size=100&ordering=-created_at"),
          api.get<Paginated<OpportunityApplication> | OpportunityApplication[]>("/opportunities/applications/?recruiter=1&page_size=100&ordering=-applied_at"),
          api.get<Paginated<Talent> | Talent[]>("/opportunities/talents/?page_size=60"),
          api.get<Paginated<TalentBookmark> | TalentBookmark[]>("/opportunities/talent-bookmarks/?page_size=100"),
          api.get<EmployerAnalytics>("/opportunities/employer-profile/analytics/"),
        ]);
        if (jobs.status === "fulfilled") setOpportunities(unwrap(jobs.value));
        if (apps.status === "fulfilled") setApplications(unwrap(apps.value));
        if (talentData.status === "fulfilled") setTalents(unwrap(talentData.value));
        if (saved.status === "fulfilled") setBookmarks(unwrap(saved.value));
        if (stats.status === "fulfilled") setAnalytics(stats.value);
        const failures = [jobs, apps, talentData, saved, stats].filter((result) => result.status === "rejected");
        if (failures.length) setError("Certaines données du tableau de bord n'ont pas pu être chargées. Réessayez dans quelques instants.");
      }
    } catch (e) { setError(e instanceof ApiError ? e.message : "Impossible de charger l'espace recruteur."); }
    finally { setLoading(false); }
  }

  useEffect(() => { if (ready) void load(); }, [ready]);

  async function saveEmployer(e: React.FormEvent) {
    e.preventDefault(); setSaving(true); setError(""); setMessage("");
    try {
      const fd = new FormData();
      const fields: Array<keyof EmployerProfile> = [
        "company_name", "tagline", "description", "industry", "company_size", "website_url", "linkedin_url", "contact_email",
        "founded_year", "brand_color", "country", "city",
      ];
      for (const field of fields) {
        const value = profile[field];
        if (value !== undefined && value !== null) fd.append(field, String(value));
      }
      fd.append("values", JSON.stringify(profile.values || []));
      fd.append("benefits", JSON.stringify(profile.benefits || []));
      fd.append("hiring_regions", JSON.stringify(profile.hiring_regions || []));
      if (logo) fd.append("logo", logo);
      if (banner) fd.append("banner", banner);
      const saved = profile.id
        ? await api.patch<EmployerProfile>(`/opportunities/employer-profile/${profile.id}/`, fd)
        : await api.post<EmployerProfile>("/opportunities/employer-profile/", fd);
      setProfile(saved); setLogo(null); setBanner(null);
      setMessage(saved.status === "pending" ? "Profil entreprise enregistré et envoyé à validation." : "Profil entreprise et branding mis à jour.");
    } catch (e) { setError(e instanceof ApiError ? e.message : "Enregistrement impossible."); }
    finally { setSaving(false); }
  }

  function openCreateJob() {
    setEditingJob(null); setJobForm({ ...initialOpportunity }); setJobCover(null); setShowJobModal(true);
  }

  function openEditJob(job: Opportunity) {
    setEditingJob(job); setJobCover(null);
    setJobForm({
      title: job.title, kind: job.kind, contract_type: job.contract_type, work_mode: job.work_mode, experience_level: job.experience_level,
      description: job.description, department: job.department || "", openings: String(job.openings || 1),
      responsibilities: job.responsibilities.join("; "), requirements: job.requirements.join("; "),
      skills_required: job.skills_required.join(", "), skills_optional: job.skills_optional.join(", "),
      screening_questions: (job.screening_questions || []).join("; "), country: job.country || "", city: job.city || "",
      remote_worldwide: job.remote_worldwide, salary_min: job.salary_min || "", salary_max: job.salary_max || "",
      salary_currency: job.salary_currency, salary_period: job.salary_period, show_salary: job.show_salary, apply_mode: job.apply_mode,
      external_application_url: job.external_application_url || "", application_deadline: job.application_deadline ? toLocalInput(job.application_deadline) : "", status: job.status,
    });
    setShowJobModal(true);
  }

  async function saveOpportunity(e: React.FormEvent) {
    e.preventDefault(); setSaving(true); setError("");
    try {
      const fd = new FormData();
      const scalar: Record<string, string> = {
        title: jobForm.title, kind: jobForm.kind, contract_type: jobForm.contract_type, work_mode: jobForm.work_mode,
        experience_level: jobForm.experience_level, description: jobForm.description, department: jobForm.department,
        openings: jobForm.openings || "1", country: jobForm.remote_worldwide ? "" : jobForm.country, city: jobForm.remote_worldwide ? "" : jobForm.city,
        salary_min: jobForm.salary_min, salary_max: jobForm.salary_max, salary_currency: jobForm.salary_currency, salary_period: jobForm.salary_period,
        apply_mode: jobForm.apply_mode, external_application_url: jobForm.apply_mode === "external" ? jobForm.external_application_url : "",
        application_deadline: jobForm.application_deadline ? new Date(jobForm.application_deadline).toISOString() : "", status: jobForm.status,
      };
      Object.entries(scalar).forEach(([k, v]) => fd.append(k, v));
      fd.append("remote_worldwide", String(jobForm.remote_worldwide)); fd.append("show_salary", String(jobForm.show_salary));
      fd.append("responsibilities", JSON.stringify(split(jobForm.responsibilities)));
      fd.append("requirements", JSON.stringify(split(jobForm.requirements)));
      fd.append("skills_required", JSON.stringify(split(jobForm.skills_required)));
      fd.append("skills_optional", JSON.stringify(split(jobForm.skills_optional)));
      fd.append("screening_questions", JSON.stringify(split(jobForm.screening_questions)));
      if (jobCover) fd.append("cover_image", jobCover);
      if (editingJob) await api.patch(`/opportunities/listings/${editingJob.slug}/`, fd);
      else await api.post("/opportunities/listings/", fd);
      setShowJobModal(false); setEditingJob(null); setJobCover(null); setMessage(editingJob ? "Opportunité mise à jour." : "Opportunité créée."); await load();
    } catch (e) { setError(e instanceof ApiError ? e.message : "Enregistrement de l'opportunité impossible."); }
    finally { setSaving(false); }
  }

  async function updateJobStatus(job: Opportunity, status: string) {
    try { await api.patch(`/opportunities/listings/${job.slug}/`, { status }); setMessage("Statut de l'opportunité mis à jour."); await load(); }
    catch (e) { setError(e instanceof ApiError ? e.message : "Modification impossible."); }
  }

  async function saveApplicationReview(app: OpportunityApplication, patch: Partial<OpportunityApplication>) {
    try {
      const payload = {
        status: patch.status || app.status,
        recruiter_note: patch.recruiter_note ?? app.recruiter_note ?? "",
        recruiter_rating: patch.recruiter_rating ?? app.recruiter_rating ?? 0,
        recruiter_tags: patch.recruiter_tags ?? app.recruiter_tags ?? [],
        next_step_at: patch.next_step_at === undefined ? (app.next_step_at || null) : patch.next_step_at,
      };
      const updated = await api.post<OpportunityApplication>(`/opportunities/applications/${app.id}/review/`, payload);
      setApplications((rows) => rows.map((row) => row.id === app.id ? updated : row));
      setSelectedApp((current) => current?.id === app.id ? updated : current);
      setMessage("Candidature mise à jour.");
    } catch (e) { setError(e instanceof ApiError ? e.message : "Mise à jour impossible."); }
  }

  async function searchTalents() {
    try {
      const qs = new URLSearchParams({ page_size: "60" });
      if (talentSearch.trim()) qs.set("search", talentSearch.trim());
      if (talentCountry) qs.set("country", talentCountry);
      if (talentAvailability) qs.set("availability", talentAvailability);
      if (talentExperience) qs.set("min_experience", talentExperience);
      const data = await api.get<Paginated<Talent> | Talent[]>(`/opportunities/talents/?${qs.toString()}`);
      setTalents(unwrap(data));
    } catch (e) { setError(e instanceof ApiError ? e.message : "Recherche impossible."); }
  }

  async function toggleBookmark(talent: Talent) {
    const existing = bookmarks.find((b) => b.talent === talent.id);
    try {
      if (existing) await api.del(`/opportunities/talent-bookmarks/${existing.id}/`);
      else await api.post("/opportunities/talent-bookmarks/", { talent: talent.id, note: "", tags: [] });
      const saved = await api.get<Paginated<TalentBookmark> | TalentBookmark[]>("/opportunities/talent-bookmarks/?page_size=100");
      setBookmarks(unwrap(saved));
    } catch (e) { setError(e instanceof ApiError ? e.message : "Impossible de mettre à jour les favoris."); }
  }

  const visibleApplications = useMemo(() => applications.filter((app) => {
    const q = candidateSearch.trim().toLowerCase();
    const matchesText = !q || [app.candidate_name_snapshot, app.candidate_email_snapshot, app.headline_snapshot, app.opportunity_title, ...(app.skills_snapshot || [])].join(" ").toLowerCase().includes(q);
    const matchesJob = !candidateJob || String(app.opportunity) === candidateJob;
    return matchesText && matchesJob;
  }), [applications, candidateSearch, candidateJob]);

  const completeness = companyCompleteness(profile);

  if (!ready) return <GuardScreen />;
  if (loading && profile.status === "none") return <div className="container-app py-10 text-gray-500">Chargement de l'espace entreprise...</div>;

  return <div className="container-app py-8 sm:py-10">
    <DashboardNav role="employer" />
    <div className="mt-6 overflow-hidden rounded-[28px] border border-slate-200 bg-white shadow-sm">
      <CompanyHero profile={profile} completeness={completeness} onEdit={() => setTab("brand")} />
      {profile.status === "approved" && <EmployerTabs tab={tab} setTab={setTab} />}
    </div>

    {error && <div className="mt-5 rounded-2xl border border-red-100 bg-red-50 p-4 text-sm text-red-700">{error}</div>}
    {message && <div className="mt-5 rounded-2xl border border-emerald-100 bg-emerald-50 p-4 text-sm text-emerald-700">{message}</div>}

    {profile.status !== "approved" ? <div className="mt-6"><CompanyProfileForm profile={profile} setProfile={setProfile} logo={logo} setLogo={setLogo} banner={banner} setBanner={setBanner} submit={saveEmployer} saving={saving} /></div> : <div className="mt-6">
      {tab === "overview" && <OverviewTab profile={profile} analytics={analytics} opportunities={opportunities} applications={applications} completeness={completeness} onCreate={openCreateJob} onViewCandidates={() => setTab("candidates")} onEditCompany={() => setTab("brand")} />}
      {tab === "jobs" && <JobsTab jobs={opportunities} onCreate={openCreateJob} onEdit={openEditJob} onStatus={updateJobStatus} />}
      {tab === "candidates" && <CandidatesTab applications={visibleApplications} jobs={opportunities} search={candidateSearch} setSearch={setCandidateSearch} jobFilter={candidateJob} setJobFilter={setCandidateJob} onOpen={setSelectedApp} onMove={saveApplicationReview} />}
      {tab === "talents" && <TalentsTab talents={talents} bookmarks={bookmarks} search={talentSearch} setSearch={setTalentSearch} country={talentCountry} setCountry={setTalentCountry} availability={talentAvailability} setAvailability={setTalentAvailability} experience={talentExperience} setExperience={setTalentExperience} onSearch={searchTalents} onBookmark={toggleBookmark} />}
      {tab === "brand" && <CompanyProfileForm profile={profile} setProfile={setProfile} logo={logo} setLogo={setLogo} banner={banner} setBanner={setBanner} submit={saveEmployer} saving={saving} approved />}
    </div>}

    {showJobModal && <OpportunityModal form={jobForm} setForm={setJobForm} cover={jobCover} setCover={setJobCover} existingCover={editingJob?.cover_image || null} onClose={() => setShowJobModal(false)} onSubmit={saveOpportunity} saving={saving} editing={Boolean(editingJob)} />}
    {selectedApp && <ApplicationDrawer app={selectedApp} onClose={() => setSelectedApp(null)} onSave={saveApplicationReview} />}
  </div>;
}

function CompanyHero({ profile, completeness, onEdit }: { profile: EmployerProfile; completeness: number; onEdit: () => void }) {
  const bannerStyle = profile.banner ? { backgroundImage: `linear-gradient(90deg, rgba(4,17,41,.80), rgba(4,17,41,.28)), url(${profile.banner})` } : undefined;
  return <div className="relative min-h-[230px] overflow-hidden bg-gradient-to-br from-[#071a38] via-[#0c2854] to-[#153d77] bg-cover bg-center px-5 py-7 text-white sm:px-8" style={bannerStyle}>
    <div className="absolute inset-0 bg-[radial-gradient(circle_at_80%_20%,rgba(255,104,39,.24),transparent_28%)]" />
    <div className="relative flex flex-col justify-between gap-8 sm:flex-row sm:items-end">
      <div className="flex items-start gap-4 sm:gap-5">
        <div className="grid h-20 w-20 shrink-0 place-items-center overflow-hidden rounded-2xl border-4 border-white/90 bg-white text-[#0b2142] shadow-xl sm:h-24 sm:w-24">
          {profile.logo ? <img loading="lazy" decoding="async" src={profile.logo} alt={`Logo ${profile.company_name || "entreprise"}`} className="h-full w-full object-contain p-1" /> : <Building2 size={36} />}
        </div>
        <div className="pt-1"><div className="flex flex-wrap items-center gap-2"><span className="rounded-full bg-white/12 px-2.5 py-1 text-[11px] font-semibold backdrop-blur">Espace entreprise</span>{profile.status !== "none" && <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${profile.status === "approved" ? "bg-emerald-400/20 text-emerald-100" : "bg-amber-300/20 text-amber-100"}`}>{profile.status === "approved" ? "Entreprise vérifiée" : "Validation en cours"}</span>}</div><h1 className="mt-3 text-2xl font-extrabold sm:text-3xl">{profile.company_name || "Votre entreprise"}</h1><p className="mt-1 max-w-2xl text-sm text-blue-100">{profile.tagline || "Construisez votre marque employeur, publiez vos offres et pilotez vos recrutements depuis un seul espace."}</p><div className="mt-3 flex flex-wrap gap-3 text-xs text-blue-100">{profile.industry && <span>{profile.industry}</span>}{(profile.city || profile.country) && <span className="flex items-center gap-1"><MapPin size={12} /> {[profile.city, profile.country].filter(Boolean).join(", ")}</span>}{profile.company_size && <span>{profile.company_size} collaborateurs</span>}</div></div>
      </div>
      <div className="flex items-center gap-3"><div className="hidden rounded-2xl bg-white/10 px-4 py-3 text-right backdrop-blur sm:block"><p className="text-[10px] uppercase tracking-wider text-blue-200">Profil complété</p><p className="text-xl font-extrabold">{completeness}%</p></div>{profile.status === "approved" && <button onClick={onEdit} className="inline-flex items-center gap-2 rounded-xl bg-white px-4 py-2.5 text-sm font-bold text-[#0b2142] shadow"><FilePenLine size={15} /> Modifier le profil</button>}</div>
    </div>
  </div>;
}

function EmployerTabs({ tab, setTab }: { tab: Tab; setTab: (tab: Tab) => void }) {
  const rows: Array<[Tab, string, React.ReactNode]> = [
    ["overview", "Vue d'ensemble", <LayoutDashboard size={16} />], ["jobs", "Offres", <BriefcaseBusiness size={16} />],
    ["candidates", "Candidatures", <UsersRound size={16} />], ["talents", "Talents", <UserRoundSearch size={16} />], ["brand", "Profil entreprise", <Building2 size={16} />],
  ];
  return <div className="overflow-x-auto border-t border-slate-100 bg-white"><div className="flex min-w-max gap-1 px-3 py-2 sm:px-5">{rows.map(([id, label, icon]) => <button key={id} onClick={() => setTab(id)} className={`flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-semibold transition ${tab === id ? "bg-orange-50 text-orange-700" : "text-slate-600 hover:bg-slate-50 hover:text-slate-900"}`}>{icon}{label}</button>)}</div></div>;
}

function OverviewTab({ profile, analytics, opportunities, applications, completeness, onCreate, onViewCandidates, onEditCompany }: { profile: EmployerProfile; analytics: EmployerAnalytics | null; opportunities: Opportunity[]; applications: OpportunityApplication[]; completeness: number; onCreate: () => void; onViewCandidates: () => void; onEditCompany: () => void }) {
  const recent = applications.slice(0, 5);
  return <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_340px]">
    <div className="space-y-6">
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><Metric icon={<BriefcaseBusiness size={18}/>} label="Offres publiées" value={analytics?.published ?? opportunities.filter((x) => x.status === "published").length} /><Metric icon={<UsersRound size={18}/>} label="Candidatures" value={analytics?.applications_total ?? applications.length} /><Metric icon={<CalendarClock size={18}/>} label="Entretiens" value={analytics?.interviews ?? 0} /><Metric icon={<UserCheck size={18}/>} label="Recrutements" value={analytics?.hires ?? 0} /></section>
      <section className="card p-5 sm:p-6"><div className="flex items-center justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-wider text-slate-400">Pipeline</p><h2 className="mt-1 text-lg font-extrabold">Où en sont vos candidats ?</h2></div><button onClick={onViewCandidates} className="btn-outline !py-2 !text-xs">Ouvrir l'ATS <ChevronRight size={14}/></button></div><div className="mt-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{["submitted","reviewing","shortlisted","interview","offer","hired"].map((status) => { const value = analytics?.pipeline?.[status] ?? applications.filter((x) => x.status === status).length; return <div key={status} className="rounded-2xl border border-slate-100 bg-slate-50/70 p-4"><div className="flex items-center justify-between"><span className="text-xs font-semibold text-slate-500">{statusLabel[status]}</span><span className={`rounded-full px-2 py-1 text-[10px] font-bold ${statusTone[status]}`}>{value}</span></div><div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-200"><div className="h-full rounded-full bg-orange-500" style={{ width: `${Math.min(100, value * 12)}%` }} /></div></div> })}</div></section>
      <section className="card overflow-hidden"><div className="border-b border-slate-100 p-5"><h2 className="font-extrabold">Candidatures récentes</h2><p className="mt-1 text-xs text-slate-500">Les derniers profils entrés dans votre pipeline.</p></div>{recent.length ? <div className="divide-y divide-slate-100">{recent.map((app) => <div key={app.id} className="flex flex-wrap items-center justify-between gap-3 p-4 sm:px-5"><div><p className="font-bold">{app.candidate_name_snapshot}</p><p className="mt-0.5 text-xs text-slate-500">{app.opportunity_title} · Match {app.match_score}%</p></div><span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${statusTone[app.status] || "bg-slate-100 text-slate-600"}`}>{statusLabel[app.status] || app.status}</span></div>)}</div> : <Empty text="Aucune candidature pour le moment." />}</section>
    </div>
    <aside className="space-y-5"><section className="card p-5"><h3 className="font-extrabold">Actions rapides</h3><div className="mt-4 space-y-2"><button onClick={onCreate} className="btn-primary w-full"><Plus size={15}/> Publier une opportunité</button><button onClick={onViewCandidates} className="btn-outline w-full"><UsersRound size={15}/> Gérer les candidatures</button><Link href="/opportunities" className="btn-outline w-full"><Eye size={15}/> Voir le marché public</Link></div></section><section className="card p-5"><div className="flex items-center justify-between"><h3 className="font-extrabold">Marque employeur</h3><span className="text-sm font-extrabold text-orange-600">{completeness}%</span></div><div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100"><div className="h-full rounded-full bg-orange-500" style={{ width: `${completeness}%` }} /></div><p className="mt-3 text-xs leading-5 text-slate-500">Ajoutez logo, bannière, valeurs, avantages et zones de recrutement pour rassurer davantage les candidats.</p><button onClick={onEditCompany} className="mt-4 text-sm font-bold text-orange-700">Compléter le profil →</button>{profile.slug && <Link href={`/companies/${profile.slug}`} className="mt-2 block text-sm font-semibold text-slate-600">Voir la page entreprise publique →</Link>}</section></aside>
  </div>;
}

function JobsTab({ jobs, onCreate, onEdit, onStatus }: { jobs: Opportunity[]; onCreate: () => void; onEdit: (job: Opportunity) => void; onStatus: (job: Opportunity, status: string) => void }) {
  return <section className="card overflow-hidden"><div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 p-5 sm:p-6"><div><h2 className="text-lg font-extrabold">Vos opportunités</h2><p className="mt-1 text-xs text-slate-500">Gérez le visuel, le contenu, le statut et le volume de candidatures de chaque offre.</p></div><button onClick={onCreate} className="btn-primary"><Plus size={15}/> Nouvelle offre</button></div><div className="divide-y divide-slate-100">{jobs.length ? jobs.map((job) => <div key={job.id} className="grid gap-4 p-4 sm:p-5 lg:grid-cols-[88px_minmax(0,1fr)_auto] lg:items-center"><div className="h-20 w-full overflow-hidden rounded-xl bg-slate-100 lg:w-20">{job.cover_image ? <img loading="lazy" decoding="async" src={job.cover_image} alt="" className="h-full w-full object-cover" /> : <div className="grid h-full place-items-center text-slate-400"><ImagePlus size={24}/></div>}</div><div><div className="flex flex-wrap items-center gap-2"><span className={`rounded-full px-2 py-1 text-[10px] font-bold ${job.status === "published" ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600"}`}>{job.status}</span>{job.department && <span className="text-xs text-slate-400">{job.department}</span>}</div><Link href={`/opportunities/${job.slug}`} className="mt-1 block font-extrabold hover:text-orange-700">{job.title}</Link><p className="mt-1 text-xs text-slate-500">{job.remote_worldwide ? "Monde entier" : [job.city, job.country].filter(Boolean).join(", ")} · {job.openings || 1} poste(s) · {job.applications_count || 0} candidature(s)</p></div><div className="flex flex-wrap gap-2"><button onClick={() => onEdit(job)} className="btn-outline !py-2 !text-xs"><FilePenLine size={13}/> Modifier</button><select value={job.status} onChange={(e) => onStatus(job, e.target.value)} className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold"><option value="draft">Brouillon</option><option value="published">Publiée</option><option value="closed">Clôturée</option><option value="archived">Archivée</option></select></div></div>) : <Empty text="Aucune opportunité. Créez votre première offre avec un visuel et une description complète." />}</div></section>;
}

function CandidatesTab({ applications, jobs, search, setSearch, jobFilter, setJobFilter, onOpen, onMove }: { applications: OpportunityApplication[]; jobs: Opportunity[]; search: string; setSearch: (v: string) => void; jobFilter: string; setJobFilter: (v: string) => void; onOpen: (app: OpportunityApplication) => void; onMove: (app: OpportunityApplication, patch: Partial<OpportunityApplication>) => void }) {
  return <div className="space-y-4"><div className="card flex flex-wrap items-center gap-3 p-4"><div className="relative min-w-[220px] flex-1"><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"/><input value={search} onChange={(e) => setSearch(e.target.value)} className="input-admin w-full !pl-9" placeholder="Nom, email, compétence, poste..." /></div><select value={jobFilter} onChange={(e) => setJobFilter(e.target.value)} className="input-admin !w-auto min-w-[220px]"><option value="">Toutes les offres</option>{jobs.map((job) => <option key={job.id} value={job.id}>{job.title}</option>)}</select><span className="rounded-xl bg-slate-100 px-3 py-2 text-xs font-bold text-slate-600">{applications.length} candidat(s)</span></div><div className="overflow-x-auto pb-2"><div className="grid min-w-[1300px] grid-cols-7 gap-3">{pipelineStatuses.map((status) => { const rows = applications.filter((app) => app.status === status); return <section key={status} className="rounded-2xl border border-slate-200 bg-slate-50/70"><div className="flex items-center justify-between border-b border-slate-200 px-3 py-3"><span className="text-xs font-extrabold">{statusLabel[status]}</span><span className="rounded-full bg-white px-2 py-0.5 text-[10px] font-bold text-slate-500">{rows.length}</span></div><div className="space-y-2 p-2">{rows.map((app) => <div key={app.id} className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm"><button onClick={() => onOpen(app)} className="w-full text-left"><div className="flex items-start justify-between gap-2"><div><p className="line-clamp-1 text-sm font-extrabold">{app.candidate_name_snapshot}</p><p className="mt-0.5 line-clamp-2 text-[10px] text-slate-500">{app.opportunity_title}</p></div><span className="rounded-md bg-violet-50 px-1.5 py-1 text-[10px] font-bold text-violet-700">{app.match_score}%</span></div>{(app.recruiter_rating || 0) > 0 && <div className="mt-2 flex gap-0.5">{[1,2,3,4,5].map((n) => <Star key={n} size={11} className={n <= (app.recruiter_rating || 0) ? "fill-amber-400 text-amber-400" : "text-slate-200"} />)}</div>}{app.recruiter_tags && app.recruiter_tags.length > 0 && <div className="mt-2 flex flex-wrap gap-1">{app.recruiter_tags.slice(0,2).map((tag) => <span key={tag} className="rounded-full bg-slate-100 px-1.5 py-0.5 text-[9px] text-slate-600">{tag}</span>)}</div>}</button>{status !== "rejected" && status !== "hired" && <select value={app.status} onChange={(e) => void onMove(app, { status: e.target.value })} className="mt-2 w-full rounded-lg border border-slate-200 px-2 py-1.5 text-[10px]"><option value={app.status}>{statusLabel[app.status]}</option>{pipelineStatuses.filter((x) => x !== app.status && x !== "submitted").map((x) => <option key={x} value={x}>→ {statusLabel[x]}</option>)}</select>}</div>)}{!rows.length && <div className="p-4 text-center text-[10px] text-slate-400">Aucun profil</div>}</div></section> })}</div></div></div>;
}

function TalentsTab({ talents, bookmarks, search, setSearch, country, setCountry, availability, setAvailability, experience, setExperience, onSearch, onBookmark }: { talents: Talent[]; bookmarks: TalentBookmark[]; search: string; setSearch: (v: string) => void; country: string; setCountry: (v: string) => void; availability: string; setAvailability: (v: string) => void; experience: string; setExperience: (v: string) => void; onSearch: () => void; onBookmark: (talent: Talent) => void }) {
  const savedIds = new Set(bookmarks.map((b) => b.talent));
  return <div className="space-y-5"><section className="card p-4 sm:p-5"><div><h2 className="text-lg font-extrabold">Vivier de talents</h2><p className="mt-1 text-xs text-slate-500">Recherche multi-critères parmi les candidats ayant volontairement activé leur visibilité recruteur.</p></div><div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_180px_180px_150px_auto]"><input value={search} onChange={(e) => setSearch(e.target.value)} onKeyDown={(e) => e.key === "Enter" && void onSearch()} className="input-admin" placeholder="Compétence, métier, nom..."/><CountrySelect value={country} onChange={setCountry}/><select value={availability} onChange={(e) => setAvailability(e.target.value)} className="input-admin"><option value="">Toute disponibilité</option><option value="immediate">Immédiate</option><option value="2_weeks">Sous 2 semaines</option><option value="1_month">Sous 1 mois</option><option value="open">À l'écoute</option></select><select value={experience} onChange={(e) => setExperience(e.target.value)} className="input-admin"><option value="">Expérience</option><option value="1">1+ an</option><option value="3">3+ ans</option><option value="5">5+ ans</option><option value="8">8+ ans</option></select><button onClick={onSearch} className="btn-primary"><Search size={14}/> Rechercher</button></div></section><section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{talents.map((talent) => <article key={talent.id} className="card p-5"><div className="flex items-start justify-between gap-3"><div className="flex gap-3"><div className="grid h-12 w-12 shrink-0 place-items-center overflow-hidden rounded-xl bg-slate-100 text-slate-500">{talent.avatar ? <img loading="lazy" decoding="async" src={talent.avatar} alt="" className="h-full w-full object-cover"/> : <UsersRound size={20}/>}</div><div><h3 className="font-extrabold">{talent.full_name}</h3><p className="mt-0.5 text-xs text-slate-500">{talent.headline || "Talent KalanPro"}</p><p className="mt-1 text-[11px] text-slate-400">{talent.country} · {talent.years_experience} an(s) d'expérience</p></div></div><button onClick={() => void onBookmark(talent)} title={savedIds.has(talent.id) ? "Retirer des favoris" : "Ajouter aux favoris"} className={`rounded-xl p-2 ${savedIds.has(talent.id) ? "bg-amber-50 text-amber-600" : "bg-slate-50 text-slate-400 hover:text-amber-600"}`}><Star size={17} className={savedIds.has(talent.id) ? "fill-current" : ""}/></button></div><p className="mt-4 line-clamp-3 text-xs leading-5 text-slate-600">{talent.summary || "Profil professionnel visible aux recruteurs vérifiés."}</p><div className="mt-3 flex flex-wrap gap-1.5">{talent.skills.slice(0,7).map((skill) => <span key={skill} className="rounded-full bg-slate-100 px-2 py-1 text-[10px] font-medium text-slate-600">{skill}</span>)}</div><div className="mt-4 flex items-center gap-2">{talent.portfolio_slug && <Link href={`/portfolio/${talent.portfolio_slug}`} className="btn-outline !py-1.5 !text-xs">Portfolio</Link>}<span className="ml-auto text-[10px] font-semibold text-emerald-700">{availabilityLabel(talent.availability)}</span></div></article>)}</section>{!talents.length && <Empty text="Aucun talent ne correspond à ces critères." />}</div>;
}

function CompanyProfileForm({ profile, setProfile, logo, setLogo, banner, setBanner, submit, saving, approved = false }: { profile: EmployerProfile; setProfile: (p: EmployerProfile) => void; logo: File | null; setLogo: (f: File | null) => void; banner: File | null; setBanner: (f: File | null) => void; submit: (e: React.FormEvent) => void; saving: boolean; approved?: boolean }) {
  const logoPreview = logo ? URL.createObjectURL(logo) : profile.logo || "";
  const bannerPreview = banner ? URL.createObjectURL(banner) : profile.banner || "";
  return <form onSubmit={submit} className="space-y-5"><section className="card overflow-hidden"><div className="border-b border-slate-100 p-5 sm:p-6"><h2 className="text-lg font-extrabold">Identité & marque employeur</h2><p className="mt-1 text-xs text-slate-500">Ces éléments apparaissent sur vos offres et sur votre page entreprise publique.</p>{profile.status !== "none" && profile.status !== "approved" && <div className={`mt-3 rounded-xl p-3 text-sm ${profile.status === "pending" ? "bg-amber-50 text-amber-800" : "bg-red-50 text-red-700"}`}>Statut : <strong>{profile.status}</strong>{profile.review_note ? ` · ${profile.review_note}` : ""}</div>}</div><div className="p-5 sm:p-6"><div className="relative h-40 overflow-hidden rounded-2xl border border-dashed border-slate-300 bg-gradient-to-br from-slate-800 to-blue-900 bg-cover bg-center" style={bannerPreview ? { backgroundImage: `linear-gradient(rgba(2,12,30,.28),rgba(2,12,30,.28)),url(${bannerPreview})` } : undefined}><label className="absolute right-3 top-3 cursor-pointer rounded-xl bg-white/95 px-3 py-2 text-xs font-bold text-slate-700 shadow"><ImagePlus size={14} className="mr-1 inline"/> Bannière<input type="file" accept="image/jpeg,image/png,image/webp,image/avif" onChange={(e) => setBanner(e.target.files?.[0] || null)} className="hidden"/></label></div><div className="-mt-10 ml-5 flex items-end gap-4"><div className="grid h-24 w-24 place-items-center overflow-hidden rounded-2xl border-4 border-white bg-white shadow-lg">{logoPreview ? <img loading="lazy" decoding="async" src={logoPreview} alt="Logo aperçu" className="h-full w-full object-contain p-1"/> : <Building2 size={30} className="text-slate-400"/>}</div><label className="mb-1 cursor-pointer text-xs font-bold text-orange-700">Changer le logo<input type="file" accept="image/jpeg,image/png,image/webp,image/avif" onChange={(e) => setLogo(e.target.files?.[0] || null)} className="hidden"/></label></div></div></section><section className="card p-5 sm:p-6"><div className="grid gap-4 md:grid-cols-2"><Field label="Nom de l'entreprise"><input required value={profile.company_name || ""} onChange={(e) => setProfile({ ...profile, company_name: e.target.value })} className="input-admin w-full"/></Field><Field label="Accroche"><input value={profile.tagline || ""} onChange={(e) => setProfile({ ...profile, tagline: e.target.value })} className="input-admin w-full" placeholder="Ex. Construire les services financiers de demain"/></Field><Field label="Secteur"><input value={profile.industry || ""} onChange={(e) => setProfile({ ...profile, industry: e.target.value })} className="input-admin w-full" placeholder="Fintech, EdTech, Santé..."/></Field><Field label="Taille"><select value={profile.company_size || ""} onChange={(e) => setProfile({ ...profile, company_size: e.target.value })} className="input-admin w-full"><option value="">Non précisé</option><option value="solo">Indépendant</option><option value="1-10">1–10</option><option value="11-50">11–50</option><option value="51-200">51–200</option><option value="201-1000">201–1000</option><option value="1000+">1000+</option></select></Field><Field label="Pays"><CountrySelect required value={profile.country || ""} onChange={(v) => setProfile({ ...profile, country: v })}/></Field><Field label="Ville"><input value={profile.city || ""} onChange={(e) => setProfile({ ...profile, city: e.target.value })} className="input-admin w-full"/></Field><Field label="Année de création"><input type="number" min="1800" max={new Date().getFullYear()} value={profile.founded_year || ""} onChange={(e) => setProfile({ ...profile, founded_year: e.target.value ? Number(e.target.value) : null })} className="input-admin w-full"/></Field><Field label="Couleur de marque"><div className="flex gap-2"><input type="color" value={profile.brand_color || "#ff5a1f"} onChange={(e) => setProfile({ ...profile, brand_color: e.target.value })} className="h-11 w-14 rounded-lg border border-slate-200 p-1"/><input value={profile.brand_color || "#ff5a1f"} onChange={(e) => setProfile({ ...profile, brand_color: e.target.value })} className="input-admin flex-1"/></div></Field><Field label="Site web"><input type="url" value={profile.website_url || ""} onChange={(e) => setProfile({ ...profile, website_url: e.target.value })} className="input-admin w-full" placeholder="https://..."/></Field><Field label="LinkedIn"><input type="url" value={profile.linkedin_url || ""} onChange={(e) => setProfile({ ...profile, linkedin_url: e.target.value })} className="input-admin w-full" placeholder="https://linkedin.com/company/..."/></Field><Field label="Email recrutement"><input type="email" value={profile.contact_email || ""} onChange={(e) => setProfile({ ...profile, contact_email: e.target.value })} className="input-admin w-full"/></Field><Field label="Zones de recrutement"><input value={(profile.hiring_regions || []).join(", ")} onChange={(e) => setProfile({ ...profile, hiring_regions: split(e.target.value) })} className="input-admin w-full" placeholder="Côte d'Ivoire, Sénégal, Remote..."/></Field><Field label="Présentation" wide><textarea required rows={6} value={profile.description || ""} onChange={(e) => setProfile({ ...profile, description: e.target.value })} className="input-admin w-full" placeholder="Présentez votre mission, votre activité et votre culture."/></Field><Field label="Valeurs" wide><input value={(profile.values || []).join(", ")} onChange={(e) => setProfile({ ...profile, values: split(e.target.value) })} className="input-admin w-full" placeholder="Impact, transparence, autonomie, excellence"/></Field><Field label="Avantages candidats" wide><textarea rows={3} value={(profile.benefits || []).join("; ")} onChange={(e) => setProfile({ ...profile, benefits: split(e.target.value) })} className="input-admin w-full" placeholder="Télétravail; budget formation; assurance santé; horaires flexibles"/></Field></div><div className="mt-5 flex flex-wrap items-center gap-3"><button disabled={saving || profile.status === "suspended"} className="btn-primary">{saving ? <Loader2 size={15} className="animate-spin"/> : <CheckCircle2 size={15}/>} {profile.status === "none" ? "Envoyer pour validation" : approved ? "Enregistrer le profil entreprise" : "Mettre à jour ma demande"}</button>{approved && profile.slug && <Link href={`/companies/${profile.slug}`} className="btn-outline"><ExternalLink size={14}/> Prévisualiser la page publique</Link>}</div></section></form>;
}

function OpportunityModal({ form, setForm, cover, setCover, existingCover, onClose, onSubmit, saving, editing }: { form: typeof initialOpportunity; setForm: (x: typeof initialOpportunity) => void; cover: File | null; setCover: (f: File | null) => void; existingCover: string | null; onClose: () => void; onSubmit: (e: React.FormEvent) => void; saving: boolean; editing: boolean }) {
  const preview = cover ? URL.createObjectURL(cover) : existingCover || "";
  return <div className="fixed inset-0 z-[90] grid place-items-center bg-black/55 p-3 sm:p-4"><form onSubmit={onSubmit} className="card max-h-[94vh] w-full max-w-5xl overflow-y-auto p-5 sm:p-6"><div className="flex items-start justify-between gap-3"><div><h2 className="text-xl font-extrabold">{editing ? "Modifier l'opportunité" : "Nouvelle opportunité"}</h2><p className="mt-1 text-xs text-slate-500">Ajoutez un visuel, le contexte du poste et des questions de présélection.</p></div><button type="button" onClick={onClose} className="rounded-lg p-2 hover:bg-slate-100"><X size={18}/></button></div><div className="mt-5 grid gap-5 lg:grid-cols-[280px_minmax(0,1fr)]"><div><div className="aspect-[4/3] overflow-hidden rounded-2xl border border-dashed border-slate-300 bg-slate-50">{preview ? <img loading="lazy" decoding="async" src={preview} alt="Aperçu offre" className="h-full w-full object-cover"/> : <div className="grid h-full place-items-center text-center text-slate-400"><div><ImagePlus size={32} className="mx-auto"/><p className="mt-2 text-xs">Visuel de l'offre</p></div></div>}</div><label className="btn-outline mt-3 w-full cursor-pointer !text-xs"><ImagePlus size={14}/> Ajouter / changer le visuel<input type="file" accept="image/jpeg,image/png,image/webp,image/avif" onChange={(e) => setCover(e.target.files?.[0] || null)} className="hidden"/></label><div className="mt-4 rounded-xl bg-slate-50 p-3 text-xs leading-5 text-slate-500">Conseil : utilisez un visuel 4:3 ou 16:9 lié au métier, à votre équipe ou à votre environnement de travail.</div></div><div className="grid gap-4 md:grid-cols-2"><Field label="Titre"><input required value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} className="input-admin w-full"/></Field><Field label="Département / équipe"><input value={form.department} onChange={(e) => setForm({ ...form, department: e.target.value })} className="input-admin w-full" placeholder="Produit, Finance, Marketing..."/></Field><Field label="Type"><select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })} className="input-admin w-full"><option value="job">Emploi</option><option value="internship">Stage</option><option value="freelance">Freelance</option><option value="mission">Mission</option></select></Field><Field label="Nombre de postes"><input type="number" min="1" max="500" value={form.openings} onChange={(e) => setForm({ ...form, openings: e.target.value })} className="input-admin w-full"/></Field><Field label="Contrat"><select value={form.contract_type} onChange={(e) => setForm({ ...form, contract_type: e.target.value })} className="input-admin w-full"><option value="full_time">Temps plein</option><option value="part_time">Temps partiel</option><option value="permanent">CDI</option><option value="fixed_term">CDD</option><option value="internship">Stage</option><option value="freelance">Freelance</option><option value="project">Projet / mission</option></select></Field><Field label="Mode"><select value={form.work_mode} onChange={(e) => setForm({ ...form, work_mode: e.target.value })} className="input-admin w-full"><option value="remote">À distance</option><option value="hybrid">Hybride</option><option value="onsite">Sur site</option></select></Field><Field label="Niveau"><select value={form.experience_level} onChange={(e) => setForm({ ...form, experience_level: e.target.value })} className="input-admin w-full"><option value="entry">Premier emploi</option><option value="junior">Junior</option><option value="mid">Intermédiaire</option><option value="senior">Senior</option><option value="lead">Lead / management</option></select></Field><Field label="Candidature"><select value={form.apply_mode} onChange={(e) => setForm({ ...form, apply_mode: e.target.value })} className="input-admin w-full"><option value="internal">Dans KalanPro</option><option value="external">Lien externe</option></select></Field>{form.apply_mode === "external" && <Field label="Lien externe" wide><input type="url" required value={form.external_application_url} onChange={(e) => setForm({ ...form, external_application_url: e.target.value })} className="input-admin w-full"/></Field>}<Field label="Description" wide><textarea required rows={6} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className="input-admin w-full"/></Field><Field label="Missions (séparées par ;)" wide><textarea rows={3} value={form.responsibilities} onChange={(e) => setForm({ ...form, responsibilities: e.target.value })} className="input-admin w-full"/></Field><Field label="Exigences"><textarea rows={4} value={form.requirements} onChange={(e) => setForm({ ...form, requirements: e.target.value })} className="input-admin w-full"/></Field><Field label="Questions de présélection"><textarea rows={4} value={form.screening_questions} onChange={(e) => setForm({ ...form, screening_questions: e.target.value })} className="input-admin w-full" placeholder="Pourquoi ce poste ?; Quel est votre préavis ?"/></Field><Field label="Compétences requises"><input value={form.skills_required} onChange={(e) => setForm({ ...form, skills_required: e.target.value })} className="input-admin w-full" placeholder="Excel, Power BI, SQL"/></Field><Field label="Compétences bonus"><input value={form.skills_optional} onChange={(e) => setForm({ ...form, skills_optional: e.target.value })} className="input-admin w-full"/></Field><div className="md:col-span-2"><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.remote_worldwide} onChange={(e) => setForm({ ...form, remote_worldwide: e.target.checked })}/><span>Ouvert au télétravail depuis n'importe quel pays</span></label></div>{!form.remote_worldwide && <><Field label="Pays"><CountrySelect value={form.country} onChange={(v) => setForm({ ...form, country: v })}/></Field><Field label="Ville"><input value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} className="input-admin w-full"/></Field></>}<Field label="Rémunération min"><input type="number" min="0" value={form.salary_min} onChange={(e) => setForm({ ...form, salary_min: e.target.value })} className="input-admin w-full"/></Field><Field label="Rémunération max"><input type="number" min="0" value={form.salary_max} onChange={(e) => setForm({ ...form, salary_max: e.target.value })} className="input-admin w-full"/></Field><Field label="Devise"><select value={form.salary_currency} onChange={(e) => setForm({ ...form, salary_currency: e.target.value })} className="input-admin w-full"><option>XOF</option><option>XAF</option><option>EUR</option><option>MAD</option><option>USD</option></select></Field><Field label="Période"><select value={form.salary_period} onChange={(e) => setForm({ ...form, salary_period: e.target.value })} className="input-admin w-full"><option value="month">Par mois</option><option value="year">Par an</option><option value="day">Par jour</option><option value="hour">Par heure</option><option value="project">Forfait mission</option></select></Field><Field label="Clôture"><input type="datetime-local" value={form.application_deadline} onChange={(e) => setForm({ ...form, application_deadline: e.target.value })} className="input-admin w-full"/></Field><Field label="Statut"><select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })} className="input-admin w-full"><option value="draft">Brouillon</option><option value="published">Publier</option><option value="closed">Clôturée</option><option value="archived">Archivée</option></select></Field><div className="md:col-span-2"><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={form.show_salary} onChange={(e) => setForm({ ...form, show_salary: e.target.checked })}/><span>Afficher la rémunération aux candidats</span></label></div></div></div><div className="mt-6 flex justify-end gap-2"><button type="button" onClick={onClose} className="btn-outline">Annuler</button><button disabled={saving} className="btn-primary">{saving ? <Loader2 size={15} className="animate-spin"/> : <BriefcaseBusiness size={15}/>} {editing ? "Enregistrer les modifications" : "Créer l'opportunité"}</button></div></form></div>;
}

function ApplicationDrawer({ app, onClose, onSave }: { app: OpportunityApplication; onClose: () => void; onSave: (app: OpportunityApplication, patch: Partial<OpportunityApplication>) => void }) {
  const [note, setNote] = useState(app.recruiter_note || "");
  const [rating, setRating] = useState(app.recruiter_rating || 0);
  const [tagsText, setTagsText] = useState((app.recruiter_tags || []).join(", "));
  const [nextStep, setNextStep] = useState(app.next_step_at ? toLocalInput(app.next_step_at) : "");
  return <div className="fixed inset-0 z-[95] flex justify-end bg-black/40"><div className="h-full w-full max-w-xl overflow-y-auto bg-white shadow-2xl"><div className="sticky top-0 z-10 flex items-start justify-between border-b border-slate-100 bg-white p-5"><div><p className="text-xs font-bold uppercase tracking-wider text-orange-600">Dossier candidat</p><h2 className="mt-1 text-xl font-extrabold">{app.candidate_name_snapshot}</h2><p className="mt-1 text-xs text-slate-500">{app.opportunity_title} · Match {app.match_score}%</p></div><button onClick={onClose} className="rounded-xl p-2 hover:bg-slate-100"><X size={18}/></button></div><div className="space-y-5 p-5"><section className="rounded-2xl bg-slate-50 p-4"><p className="text-sm font-bold">{app.headline_snapshot || "Profil KalanPro"}</p><p className="mt-1 text-xs text-slate-500">{app.candidate_email_snapshot} · {app.country_snapshot}</p><div className="mt-3 flex flex-wrap gap-1.5">{app.skills_snapshot.map((skill) => <span key={skill} className="rounded-full bg-white px-2 py-1 text-[10px] text-slate-600">{skill}</span>)}</div></section>{app.cover_letter && <section><h3 className="text-sm font-extrabold">Message du candidat</h3><p className="mt-2 whitespace-pre-line rounded-2xl border border-slate-100 p-4 text-sm leading-6 text-slate-600">{app.cover_letter}</p></section>}{app.screening_answers?.length > 0 && <section><h3 className="text-sm font-extrabold">Réponses de présélection</h3><div className="mt-2 space-y-2">{app.screening_answers.map((row, i) => <div key={i} className="rounded-xl bg-slate-50 p-3"><p className="text-xs font-bold text-slate-700">{row.question}</p><p className="mt-1 text-xs leading-5 text-slate-600">{row.answer || "—"}</p></div>)}</div></section>}<section><h3 className="text-sm font-extrabold">Preuves & documents</h3><div className="mt-2 flex flex-wrap gap-2">{app.resume_url && <button onClick={() => apiDownload(app.resume_url!, `CV-${app.candidate_name_snapshot}`)} className="btn-outline !py-1.5 !text-xs"><Download size={13}/> Télécharger le CV</button>}{app.portfolio_snapshot?.slug && <Link href={`/portfolio/${app.portfolio_snapshot.slug}`} className="btn-outline !py-1.5 !text-xs">Portfolio</Link>}{app.certificates_snapshot.slice(0,3).map((c) => <Link key={c.number} href={`/certificates/verify/${c.verification_code}`} className="btn-outline !py-1.5 !text-xs"><ShieldCheck size={13}/> {c.title}</Link>)}</div></section><section className="rounded-2xl border border-orange-100 bg-orange-50/40 p-4"><h3 className="flex items-center gap-2 text-sm font-extrabold"><Sparkles size={15} className="text-orange-600"/> Évaluation recruteur</h3><div className="mt-4"><p className="text-xs font-semibold text-slate-600">Note</p><div className="mt-1 flex gap-1">{[1,2,3,4,5].map((n) => <button key={n} type="button" onClick={() => setRating(n)}><Star size={22} className={n <= rating ? "fill-amber-400 text-amber-400" : "text-slate-300"}/></button>)}</div></div><Field label="Tags"><input value={tagsText} onChange={(e) => setTagsText(e.target.value)} className="input-admin w-full" placeholder="prioritaire, data, bilingue..."/></Field><Field label="Note interne"><textarea rows={5} value={note} onChange={(e) => setNote(e.target.value)} className="input-admin w-full" placeholder="Notes visibles uniquement par le recruteur."/></Field><Field label="Prochaine étape"><input type="datetime-local" value={nextStep} onChange={(e) => setNextStep(e.target.value)} className="input-admin w-full"/></Field><Field label="Étape du pipeline"><select value={app.status} onChange={(e) => void onSave(app, { status: e.target.value })} className="input-admin w-full">{pipelineStatuses.filter((x) => x !== "submitted" || app.status === "submitted").map((s) => <option key={s} value={s}>{statusLabel[s]}</option>)}</select></Field><button onClick={() => void onSave(app, { recruiter_note: note, recruiter_rating: rating, recruiter_tags: split(tagsText), next_step_at: nextStep ? new Date(nextStep).toISOString() : null })} className="btn-primary mt-3 w-full"><CheckCircle2 size={15}/> Enregistrer l'évaluation</button></section></div></div></div>;
}

function Metric({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) { return <div className="card p-5"><div className="flex items-start justify-between"><div><p className="text-2xl font-extrabold">{value}</p><p className="mt-1 text-xs font-medium text-slate-500">{label}</p></div><span className="rounded-xl bg-orange-50 p-2.5 text-orange-600">{icon}</span></div></div>; }
function Field({ label, children, wide = false }: { label: string; children: React.ReactNode; wide?: boolean }) { return <label className={`${wide ? "md:col-span-2" : ""} block`}><span className="mb-1.5 block text-xs font-semibold text-slate-600">{label}</span>{children}</label>; }
function Empty({ text }: { text: string }) { return <div className="rounded-2xl border border-dashed border-slate-200 bg-white p-8 text-center text-sm text-slate-500">{text}</div>; }
function split(value: string) { return value.split(/[;,\n]/).map((x) => x.trim()).filter(Boolean); }
function toLocalInput(value: string) { const d = new Date(value); const pad = (n: number) => String(n).padStart(2, "0"); return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`; }
function availabilityLabel(value: string) { return ({ immediate: "Disponible maintenant", "2_weeks": "Sous 2 semaines", "1_month": "Sous 1 mois", open: "À l'écoute" } as Record<string,string>)[value] || value; }
function companyCompleteness(profile: EmployerProfile) { const checks = [profile.company_name, profile.tagline, profile.description, profile.industry, profile.company_size, profile.website_url, profile.logo, profile.banner, profile.country, profile.city, profile.values?.length, profile.benefits?.length, profile.hiring_regions?.length]; return Math.round((checks.filter(Boolean).length / checks.length) * 100); }
