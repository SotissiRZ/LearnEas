"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { PlusCircle, Video, Users, Calendar, Loader2, AlertCircle, CheckCircle2, Trash2, BarChart3, Eye, EyeOff, Pencil, Search, ExternalLink } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { FormationSession, InteractiveFormation } from "@/types";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import GuardScreen from "@/components/ui/GuardScreen";

interface SessionReport {
  session: FormationSession & { formation_title?: string };
  organizers: { id: number; name: string; email: string }[];
  participants: { user_id: number; name: string; email: string; role: string; total_seconds: number; first_join?: string | null; last_leave?: string | null }[];
}

export default function InstructorFormationsPage() {
  const { ready } = useAuthGuard({ roles: ["instructor", "admin"], redirectTo: "/dashboard/instructor" });
  const [formations, setFormations] = useState<InteractiveFormation[]>([]);
  const [loading, setLoading] = useState(true);
  const [openId, setOpenId] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [message, setMessage] = useState("");
  const [report, setReport] = useState<SessionReport | null>(null);

  async function load() {
    const data = await api.get<InteractiveFormation[]>("/formations/my_formations/");
    setFormations(data);
    setLoading(false);
  }
  useEffect(() => { if (ready) load().catch(() => setLoading(false)); }, [ready]);

  const filtered = useMemo(() => formations.filter((f) => {
    const matchesStatus = status === "all" || (status === "published" ? f.published : !f.published);
    const q = search.trim().toLowerCase();
    return matchesStatus && (!q || `${f.title} ${f.description || ""}`.toLowerCase().includes(q));
  }), [formations, search, status]);

  async function addSession(formationId: number, sessionNumber: number, date: string) {
    await api.post("/sessions/", { formation: formationId, session_number: sessionNumber, scheduled_at: date });
    await load();
  }
  async function removeSession(id: number) {
    if (!confirm("Supprimer cette séance planifiée ?")) return;
    await api.del(`/sessions/${id}/`);
    await load();
  }
  async function togglePublished(formation: InteractiveFormation) {
    try { await api.patch(`/formations/${formation.slug}/`, { published: !formation.published }); await load(); }
    catch (e) { setMessage(e instanceof ApiError ? e.message : "Impossible de modifier la publication."); }
  }
  async function removeFormation(formation: InteractiveFormation) {
    if (!confirm(`Supprimer définitivement la formation « ${formation.title} » et son planning ?`)) return;
    try { await api.del(`/formations/${formation.slug}/`); await load(); setMessage("Formation supprimée."); }
    catch (e) { setMessage(e instanceof ApiError ? e.message : "Impossible de supprimer la formation."); }
  }
  async function showReport(id: number) {
    try { setReport(await api.get<SessionReport>(`/sessions/${id}/report/`)); }
    catch (e) { setMessage(e instanceof ApiError ? e.message : "Impossible de charger le rapport."); }
  }

  if (!ready) return <GuardScreen />;
  return <div className="min-w-0">
    <div className="mb-6 flex flex-wrap items-start justify-between gap-3"><div><h1 className="text-xl font-bold">Formations interactives</h1><p className="mt-1 text-sm text-gray-500">Gérez vos formations live, leurs informations, leur publication et leur planning.</p></div><Link href="/dashboard/instructor/formations/new" className="btn-primary !py-2 !text-sm"><PlusCircle size={16} /> Nouvelle formation</Link></div>
    <div className="card mb-4 flex flex-wrap gap-3 p-4"><div className="relative min-w-[220px] flex-1"><Search size={15} className="absolute left-3 top-2.5 text-gray-400"/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Rechercher une formation" className="w-full rounded-lg border border-gray-200 py-2 pl-9 pr-3 text-sm"/></div><select value={status} onChange={e=>setStatus(e.target.value)} className="rounded-lg border border-gray-200 px-3 py-2 text-sm"><option value="all">Tous les statuts</option><option value="published">Publiées</option><option value="draft">Brouillons</option></select></div>
    {message && <div className="mb-4 rounded-xl bg-gray-50 p-3 text-sm text-gray-600">{message}</div>}
    {loading ? <div className="card p-8 text-center text-gray-500">Chargement...</div> : filtered.length === 0 ? <div className="card p-10 text-center text-gray-500">Aucune formation correspondante.</div> : <div className="flex flex-col gap-4">
      {filtered.map((f) => <div key={f.id} className="card p-5">
        <div className="flex flex-wrap items-center justify-between gap-3"><div className="min-w-[220px]"><div className="flex flex-wrap items-center gap-2"><p className="font-bold">{f.title}</p><span className={`badge ${f.published ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-600"}`}>{f.published ? "Publiée" : "Brouillon"}</span></div><p className="mt-1 text-xs text-gray-500">{f.num_sessions} séances · {f.session_duration_minutes} min/séance · <Users size={12} className="inline" /> {f.students_count}/{f.max_students} inscrits</p></div><div className="flex flex-wrap gap-2"><Link href={`/formations/${f.slug}`} target="_blank" className="btn-outline !py-1.5 !text-xs"><ExternalLink size={13}/> Voir</Link><Link href={`/dashboard/instructor/formations/${f.id}/edit`} className="btn-outline !py-1.5 !text-xs"><Pencil size={13}/> Modifier</Link><button onClick={() => togglePublished(f)} className="btn-outline !py-1.5 !text-xs">{f.published ? <EyeOff size={14} /> : <Eye size={14} />} {f.published ? "Dépublier" : "Publier"}</button><button onClick={() => setOpenId(openId === f.id ? null : f.id)} className="btn-outline !py-1.5 !text-xs"><Calendar size={14} /> Planning</button><button onClick={()=>removeFormation(f)} className="rounded-lg border border-red-100 px-2.5 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50"><Trash2 size={13} className="mr-1 inline"/>Supprimer</button></div></div>
        {openId === f.id && <SessionManager formation={f} onAdd={addSession} onDelete={removeSession} onReport={showReport} />}
      </div>)}
    </div>}
    {report && <ReportModal report={report} onClose={()=>setReport(null)} />}
  </div>;
}

function SessionManager({ formation, onAdd, onDelete, onReport }: { formation: InteractiveFormation; onAdd: (formationId: number, sessionNumber: number, date: string) => Promise<void>; onDelete: (id: number) => Promise<void>; onReport: (id:number)=>Promise<void>; }) {
  const sessions = formation.sessions || [];
  const next = sessions.reduce((m, s) => Math.max(m, s.session_number), 0) + 1;
  const [sessionNumber, setSessionNumber] = useState(String(next)); const [date, setDate] = useState(""); const [saving, setSaving] = useState(false); const [error, setError] = useState(""); const [success, setSuccess] = useState(false);
  useEffect(() => setSessionNumber(String(next)), [next]);
  async function submit() { setError(""); setSuccess(false); if (!date) { setError("Choisissez une date et une heure."); return; } setSaving(true); try { await onAdd(formation.id, Number(sessionNumber), new Date(date).toISOString()); setDate(""); setSuccess(true); } catch (err) { setError(err instanceof ApiError ? err.message : "Erreur lors de la planification."); } finally { setSaving(false); } }
  return <div className="mt-4 border-t border-gray-100 pt-4"><div className="mb-4 max-h-64 space-y-2 overflow-y-auto pr-1">{sessions.map((s) => <div key={s.id} className="flex flex-wrap items-center gap-3 rounded-lg border border-gray-100 p-3 text-sm"><span className="badge bg-brand-50 text-brand-700">Séance {s.session_number}</span><span>{new Date(s.scheduled_at).toLocaleString("fr-FR")}</span><span className="text-gray-400">{s.duration_minutes} min prévues</span>{s.actual_duration_minutes > 0 && <span className="text-gray-500">· {s.actual_duration_minutes} min réelles</span>}<div className="ml-auto flex gap-2"><Link href={`/live/session/${s.id}`} className="font-semibold text-brand-700"><Video size={14} className="inline" /> Salle</Link><button onClick={() => onReport(s.id)} className="text-gray-500" title="Rapport"><BarChart3 size={15} /></button><button onClick={() => onDelete(s.id)} className="text-gray-400 hover:text-red-600"><Trash2 size={15} /></button></div></div>)}{sessions.length === 0 && <p className="text-xs text-gray-500">Aucune séance planifiée.</p>}</div>{sessions.length < formation.num_sessions && <div className="grid grid-cols-1 gap-2 sm:grid-cols-[130px_1fr_auto]"><input type="number" min={1} max={formation.num_sessions} value={sessionNumber} onChange={(e) => setSessionNumber(e.target.value)} className="rounded-lg border border-gray-200 px-3 py-2 text-sm" /><input type="datetime-local" value={date} onChange={(e) => setDate(e.target.value)} className="rounded-lg border border-gray-200 px-3 py-2 text-sm" /><button onClick={submit} disabled={saving} className="btn-outline !py-2 !text-xs">{saving ? <Loader2 size={14} className="animate-spin" /> : <Calendar size={14} />} Planifier</button></div>}<p className="mt-2 text-xs text-gray-400">La salle vidéo LearnEas est créée automatiquement. Aucun lien externe n'est nécessaire.</p>{error && <p className="mt-2 flex items-center gap-1 text-xs text-red-600"><AlertCircle size={12} /> {error}</p>}{success && <p className="mt-2 flex items-center gap-1 text-xs text-brand-700"><CheckCircle2 size={12} /> Séance planifiée.</p>}</div>;
}

function ReportModal({report,onClose}:{report:SessionReport;onClose:()=>void}){return <div className="fixed inset-0 z-50 grid place-items-center bg-black/40 p-4" onClick={onClose}><div className="card max-h-[80vh] w-full max-w-2xl overflow-hidden" onClick={e=>e.stopPropagation()}><div className="flex items-start justify-between border-b border-gray-100 p-5"><div><h2 className="font-bold">Rapport de séance</h2><p className="text-xs text-gray-500">Séance {report.session.session_number} · {report.session.actual_duration_minutes || 0} min réelles</p></div><button onClick={onClose} className="text-sm text-gray-500">Fermer</button></div><div className="max-h-[60vh] overflow-y-auto p-5"><p className="mb-3 text-xs text-gray-500">Organisateur(s) : {report.organizers.map(o=>o.name).join(", ")}</p><div className="space-y-2">{report.participants.map(p=><div key={`${p.user_id}-${p.role}`} className="flex items-center gap-3 rounded-xl bg-gray-50 p-3"><div className="min-w-0 flex-1"><p className="text-sm font-semibold">{p.name}</p><p className="text-[11px] text-gray-400">{p.email} · {p.role}</p></div><strong className="text-sm">{Math.round(p.total_seconds/60)} min</strong></div>)}{!report.participants.length&&<p className="py-8 text-center text-sm text-gray-400">Aucune présence enregistrée.</p>}</div></div></div></div>}
