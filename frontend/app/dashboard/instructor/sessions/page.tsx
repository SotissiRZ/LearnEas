"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { BarChart3, CalendarDays, Clock, Mail, Users, Video, X } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { FormationSession, Paginated } from "@/types";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import GuardScreen from "@/components/ui/GuardScreen";

interface Session extends FormationSession {
  formation_id: number;
  formation_title: string;
  organizer_name: string;
}

interface ReportOrganizer {
  id: number;
  name: string;
  email: string;
  avatar: string | null;
}

interface ReportParticipant {
  user_id: number;
  name: string;
  email: string;
  role: string;
  first_join: string | null;
  last_leave: string | null;
  total_seconds: number;
}

interface Report {
  session: Session;
  organizers: ReportOrganizer[];
  participants: ReportParticipant[];
}

function unwrap<T>(data: Paginated<T> | T[]): T[] {
  return Array.isArray(data) ? data : data.results;
}

function formatSeconds(seconds: number) {
  const safe = Math.max(Math.floor(Number(seconds) || 0), 0);
  const hours = Math.floor(safe / 3600);
  const minutes = Math.floor((safe % 3600) / 60);
  const remaining = safe % 60;
  if (hours > 0) return `${hours} h ${minutes} min`;
  if (minutes > 0) return `${minutes} min ${remaining} s`;
  return `${remaining} s`;
}

function roleLabel(role: string) {
  if (role === "organizer") return "Organisateur";
  if (role === "admin") return "Administrateur";
  if (role === "guest") return "Invité";
  return "Participant";
}

export default function InstructorSessionsPage() {
  const { ready } = useAuthGuard({ roles: ["instructor", "admin"], redirectTo: "/dashboard/instructor" });
  const [sessions, setSessions] = useState<Session[]>([]);
  const [filter, setFilter] = useState("upcoming");
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!ready) return;
    api.get<Paginated<Session> | Session[]>("/sessions/mine/?ordering=scheduled_at")
      .then((data) => setSessions(unwrap(data)))
      .catch((e) => setError(e instanceof ApiError ? e.message : "Impossible de charger les séances."));
  }, [ready]);

  const now = Date.now();
  const rows = useMemo(
    () => sessions.filter((session) => {
      if (filter === "all") return true;
      if (filter === "past") return session.completed || new Date(session.scheduled_at).getTime() < now;
      return !session.completed && new Date(session.scheduled_at).getTime() >= now;
    }),
    [sessions, filter, now]
  );

  async function openReport(id: number) {
    try {
      setReport(await api.get<Report>(`/sessions/${id}/report/`));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Impossible de charger le rapport.");
    }
  }

  if (!ready) return <GuardScreen />;

  return (
    <div className="min-w-0">
      <div className="mb-5">
        <h1 className="text-xl font-bold">Séances live</h1>
        <p className="mt-1 text-sm text-gray-500">Démarrez vos salles LearnEas et consultez des durées de présence réellement observées.</p>
      </div>

      {error && <div className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      <div className="card mb-4 flex gap-1.5 p-2.5">
        {[["upcoming", "À venir"], ["past", "Terminées"], ["all", "Toutes"]].map(([value, label]) => (
          <button key={value} type="button" onClick={() => setFilter(value)} className={`rounded-lg px-3 py-2 text-xs font-semibold ${filter === value ? "bg-brand-50 text-brand-700" : "text-gray-500 hover:bg-gray-50"}`}>{label}</button>
        ))}
      </div>

      <div className="grid gap-3">
        {rows.map((session) => (
          <div key={session.id} className="card flex flex-wrap items-center gap-3 p-3.5">
            <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-brand-50 text-brand-700"><CalendarDays size={17} /></span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-semibold">{session.formation_title} · séance {session.session_number}</p>
                <span className={`badge ${session.completed ? "bg-emerald-50 text-emerald-700" : session.started_at ? "bg-blue-50 text-blue-700" : "bg-gray-100 text-gray-600"}`}>{session.completed ? "Terminée" : session.started_at ? "En cours" : "Planifiée"}</span>
              </div>
              <p className="mt-1 text-xs text-gray-500"><Clock size={12} className="inline" /> {new Date(session.scheduled_at).toLocaleString("fr-FR")} · {session.duration_minutes} min prévues{session.actual_duration_seconds > 0 ? ` · ${formatSeconds(session.actual_duration_seconds)} réelles` : ""}</p>
            </div>
            <div className="flex gap-2">
              <button type="button" onClick={() => openReport(session.id)} className="btn-outline !py-1.5 !text-xs"><BarChart3 size={13} /> Rapport</button>
              {!session.completed && <Link href={`/live/session/${session.id}`} className="btn-primary !py-1.5 !text-xs"><Video size={13} /> Ouvrir la salle</Link>}
            </div>
          </div>
        ))}
        {!rows.length && <div className="card p-8 text-center text-gray-400">Aucune séance dans cette vue.</div>}
      </div>

      {report && (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/45 p-4" onClick={() => setReport(null)}>
          <div className="card max-h-[82vh] w-full max-w-3xl overflow-hidden" onClick={(event) => event.stopPropagation()}>
            <div className="flex items-start justify-between border-b border-gray-100 px-5 py-4">
              <div>
                <h2 className="font-bold">Rapport · {report.session.formation_title}</h2>
                <p className="mt-1 text-xs text-gray-500">Séance {report.session.session_number} · durée réelle : <strong className="text-gray-700">{formatSeconds(report.session.actual_duration_seconds || 0)}</strong></p>
              </div>
              <button type="button" onClick={() => setReport(null)} className="grid h-8 w-8 place-items-center rounded-lg text-gray-400 hover:bg-gray-100 hover:text-gray-700" aria-label="Fermer"><X size={16} /></button>
            </div>

            <div className="max-h-[68vh] overflow-y-auto p-5">
              <div className="mb-5">
                <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-gray-400">Organisateur</p>
                <div className="flex flex-wrap gap-2">
                  {report.organizers.map((organizer) => (
                    <div key={organizer.id} className="flex items-center gap-2 rounded-xl border border-gray-100 bg-gray-50 px-3 py-2">
                      {organizer.avatar ? <img src={organizer.avatar} alt="" className="h-9 w-9 rounded-full object-cover" /> : <span className="grid h-9 w-9 place-items-center rounded-full bg-brand-100 text-xs font-bold text-brand-700">{organizer.name.charAt(0).toUpperCase()}</span>}
                      <div><p className="text-xs font-semibold">{organizer.name}</p><p className="flex items-center gap-1 text-[10px] text-gray-400"><Mail size={10} /> {organizer.email}</p></div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mb-2 flex items-center justify-between">
                <p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400">Présences</p>
                <span className="rounded-full bg-gray-100 px-2.5 py-1 text-[10px] font-semibold text-gray-500">{report.participants.length} personne(s)</span>
              </div>
              <div className="space-y-2">
                {report.participants.map((participant) => (
                  <div key={`${participant.user_id}-${participant.role}`} className="flex flex-wrap items-center gap-3 rounded-xl border border-gray-100 bg-gray-50 p-3">
                    <span className="grid h-8 w-8 place-items-center rounded-full bg-white text-brand-600 shadow-sm"><Users size={14} /></span>
                    <div className="min-w-0 flex-1"><p className="text-sm font-semibold">{participant.name}</p><p className="text-[10px] text-gray-400">{participant.email} · {roleLabel(participant.role)}</p></div>
                    <div className="text-right"><p className="text-[10px] uppercase tracking-wide text-gray-400">Temps présent</p><strong className="text-sm">{formatSeconds(participant.total_seconds)}</strong></div>
                  </div>
                ))}
                {!report.participants.length && <p className="py-8 text-center text-sm text-gray-400">Aucune présence enregistrée.</p>}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
