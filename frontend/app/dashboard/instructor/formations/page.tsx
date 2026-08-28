"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PlusCircle, Video, Users, Calendar, Loader2, AlertCircle, CheckCircle2, Trash2, BarChart3, Eye, EyeOff } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { FormationSession, InteractiveFormation } from "@/types";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import DashboardNav from "@/components/dashboard/DashboardNav";
import GuardScreen from "@/components/ui/GuardScreen";

interface SessionReport {
  session: FormationSession;
  organizers: { id: number; name: string; email: string }[];
  participants: { user_id: number; name: string; email: string; role: string; total_seconds: number }[];
}

export default function InstructorFormationsPage() {
  const { ready } = useAuthGuard({ roles: ["instructor", "admin"], redirectTo: "/dashboard/instructor" });
  const [formations, setFormations] = useState<InteractiveFormation[]>([]);
  const [loading, setLoading] = useState(true);
  const [openId, setOpenId] = useState<number | null>(null);

  async function load() {
    const data = await api.get<InteractiveFormation[]>("/formations/my_formations/");
    setFormations(data);
    setLoading(false);
  }
  useEffect(() => { if (ready) load().catch(() => setLoading(false)); }, [ready]);

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
    await api.patch(`/formations/${formation.slug}/`, { published: !formation.published });
    await load();
  }

  if (!ready) return <GuardScreen />;
  return <div className="container-app py-10">
    <DashboardNav role="instructor" />
    <div className="mb-6 flex items-center justify-between"><h1 className="text-xl font-bold">Mes formations interactives</h1><Link href="/dashboard/instructor/formations/new" className="btn-primary !py-2 !text-sm"><PlusCircle size={16} /> Nouvelle formation</Link></div>
    {loading ? <p className="text-gray-500">Chargement...</p> : formations.length === 0 ? <div className="card p-10 text-center text-gray-500">Aucune formation interactive créée.</div> : <div className="flex flex-col gap-4">
      {formations.map((f) => <div key={f.id} className="card p-5">
        <div className="flex flex-wrap items-center justify-between gap-3"><div><div className="flex items-center gap-2"><p className="font-bold">{f.title}</p><span className={`badge ${f.published ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-600"}`}>{f.published ? "Publiée" : "Brouillon"}</span></div><p className="text-xs text-gray-500">{f.num_sessions} séances · {f.session_duration_minutes} min/séance · <Users size={12} className="inline" /> {f.students_count}/{f.max_students} inscrits</p></div><div className="flex gap-2"><button onClick={() => togglePublished(f)} className="btn-outline !py-1.5 !text-xs">{f.published ? <EyeOff size={14} /> : <Eye size={14} />} {f.published ? "Dépublier" : "Publier"}</button><button onClick={() => setOpenId(openId === f.id ? null : f.id)} className="btn-outline !py-1.5 !text-xs"><Calendar size={14} /> Gérer le planning</button></div></div>
        {openId === f.id && <SessionManager formation={f} onAdd={addSession} onDelete={removeSession} />}
      </div>)}
    </div>}
  </div>;
}

function SessionManager({ formation, onAdd, onDelete }: { formation: InteractiveFormation; onAdd: (formationId: number, sessionNumber: number, date: string) => Promise<void>; onDelete: (id: number) => Promise<void> }) {
  const sessions = formation.sessions || [];
  const next = sessions.reduce((m, s) => Math.max(m, s.session_number), 0) + 1;
  const [sessionNumber, setSessionNumber] = useState(String(next));
  const [date, setDate] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [report, setReport] = useState<SessionReport | null>(null);

  useEffect(() => setSessionNumber(String(next)), [next]);

  async function submit() {
    setError(""); setSuccess(false);
    if (!date) { setError("Choisissez une date et une heure pour la séance."); return; }
    setSaving(true);
    try { await onAdd(formation.id, Number(sessionNumber), new Date(date).toISOString()); setDate(""); setSuccess(true); }
    catch (err) { setError(err instanceof ApiError ? err.message : "Erreur lors de la planification."); }
    finally { setSaving(false); }
  }
  async function showReport(id: number) { setReport(await api.get<SessionReport>(`/sessions/${id}/report/`)); }

  return <div className="mt-4 border-t border-gray-100 pt-4">
    <div className="mb-4 flex flex-col gap-2">
      {sessions.map((s) => <div key={s.id} className="flex flex-wrap items-center gap-3 rounded-lg border border-gray-100 p-3 text-sm">
        <span className="badge bg-brand-50 text-brand-700">Séance {s.session_number}</span><span>{new Date(s.scheduled_at).toLocaleString("fr-FR")}</span><span className="text-gray-400">{s.duration_minutes} min prévues</span>
        {s.actual_duration_minutes != null && s.actual_duration_minutes > 0 && <span className="text-gray-500">· {s.actual_duration_minutes} min réelles</span>}
        <div className="ml-auto flex gap-2"><Link href={`/live/session/${s.id}`} className="font-semibold text-brand-700"><Video size={14} className="inline" /> Salle</Link><button onClick={() => showReport(s.id)} className="text-gray-500" title="Rapport"><BarChart3 size={15} /></button><button onClick={() => onDelete(s.id)} className="text-gray-400 hover:text-red-600"><Trash2 size={15} /></button></div>
      </div>)}
      {sessions.length === 0 && <p className="text-xs text-gray-500">Aucune séance planifiée.</p>}
    </div>
    {sessions.length < formation.num_sessions && <div className="grid grid-cols-1 gap-2 sm:grid-cols-[130px_1fr_auto]">
      <input type="number" min={1} max={formation.num_sessions} value={sessionNumber} onChange={(e) => setSessionNumber(e.target.value)} className="rounded-lg border border-gray-200 px-3 py-2 text-sm" />
      <input type="datetime-local" value={date} onChange={(e) => setDate(e.target.value)} className="rounded-lg border border-gray-200 px-3 py-2 text-sm" />
      <button onClick={submit} disabled={saving} className="btn-outline !py-2 !text-xs">{saving ? <Loader2 size={14} className="animate-spin" /> : <Calendar size={14} />} Planifier</button>
    </div>}
    <p className="mt-2 text-xs text-gray-400">La salle vidéo LearnEas est créée automatiquement. Aucun lien Zoom/Meet/Jitsi n'est à saisir.</p>
    {error && <p className="mt-2 flex items-center gap-1 text-xs text-red-600"><AlertCircle size={12} /> {error}</p>}{success && <p className="mt-2 flex items-center gap-1 text-xs text-brand-700"><CheckCircle2 size={12} /> Séance planifiée.</p>}
    {report && <div className="mt-4 rounded-xl bg-gray-50 p-4 text-xs"><p className="font-bold">Rapport séance {report.session.session_number}</p><p className="mt-1 text-gray-500">Organisateur(s) : {report.organizers.map((o) => o.name).join(", ")}</p><div className="mt-2 space-y-1">{report.participants.length ? report.participants.map((p) => <div key={`${p.user_id}-${p.role}`} className="flex justify-between"><span>{p.name} · {p.role}</span><span>{Math.round(p.total_seconds / 60)} min</span></div>) : <span className="text-gray-500">Aucune présence enregistrée.</span>}</div></div>}
  </div>;
}
