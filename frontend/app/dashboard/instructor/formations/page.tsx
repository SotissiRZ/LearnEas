"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PlusCircle, Video, Users, Calendar, Link as LinkIcon } from "lucide-react";
import { api } from "@/lib/api";
import { InteractiveFormation } from "@/types";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import DashboardNav from "@/components/dashboard/DashboardNav";
import GuardScreen from "@/components/ui/GuardScreen";

export default function InstructorFormationsPage() {
  const { ready } = useAuthGuard({ roles: ["instructor", "admin"], redirectTo: "/dashboard/instructor" });
  const [formations, setFormations] = useState<InteractiveFormation[]>([]);
  const [loading, setLoading] = useState(true);
  const [openId, setOpenId] = useState<number | null>(null);

  useEffect(() => {
    if (!ready) return;
    api.get<InteractiveFormation[]>("/formations/my_formations/")
      .then(setFormations)
      .finally(() => setLoading(false));
  }, [ready]);

  async function addSession(formationId: number, sessionNumber: number, date: string, link: string) {
    await api.post("/sessions/", {
      formation: formationId,
      session_number: sessionNumber,
      scheduled_at: date,
      duration_minutes: 60,
      meeting_link: link,
    });
    const updated = await api.get<InteractiveFormation[]>("/formations/my_formations/");
    setFormations(updated);
  }

  if (!ready) return <GuardScreen />;

  return (
    <div className="container-app py-10">
      <DashboardNav role="instructor" />
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold">Mes formations interactives</h1>
        <Link href="/dashboard/instructor/formations/new" className="btn-primary !py-2 !text-sm">
          <PlusCircle size={16} /> Nouvelle formation
        </Link>
      </div>

      {loading ? (
        <p className="text-gray-500">Chargement...</p>
      ) : formations.length === 0 ? (
        <div className="card p-10 text-center text-gray-500">Aucune formation interactive créée.</div>
      ) : (
        <div className="flex flex-col gap-4">
          {formations.map((f) => (
            <div key={f.id} className="card p-5">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-bold">{f.title}</p>
                  <p className="text-xs text-gray-500">
                    {f.num_sessions} séances · <Users size={12} className="inline" /> {f.students_count}/{f.max_students} inscrits
                  </p>
                </div>
                <button onClick={() => setOpenId(openId === f.id ? null : f.id)} className="btn-outline !py-1.5 !text-xs">
                  <Calendar size={14} /> Gérer le planning
                </button>
              </div>

              {openId === f.id && <SessionManager formationId={f.id} onAdd={addSession} nextSessionNumber={f.num_sessions ? undefined : 1} />}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function SessionManager({
  formationId, onAdd,
}: {
  formationId: number;
  onAdd: (formationId: number, sessionNumber: number, date: string, link: string) => void;
  nextSessionNumber?: number;
}) {
  const [sessionNumber, setSessionNumber] = useState("1");
  const [date, setDate] = useState("");
  const [link, setLink] = useState("");

  return (
    <div className="mt-4 flex flex-col gap-2 border-t border-gray-100 pt-4">
      <p className="text-sm font-semibold">Ajouter une séance</p>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        <input type="number" min={1} value={sessionNumber} onChange={(e) => setSessionNumber(e.target.value)}
          placeholder="N° séance" className="rounded-lg border border-gray-200 px-3 py-2 text-sm" />
        <input type="datetime-local" value={date} onChange={(e) => setDate(e.target.value)}
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm" />
        <div className="relative">
          <LinkIcon className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={14} />
          <input value={link} onChange={(e) => setLink(e.target.value)} placeholder="Lien Jitsi/Zoom/Meet"
            className="w-full rounded-lg border border-gray-200 py-2 pl-8 pr-3 text-sm" />
        </div>
      </div>
      <button
        onClick={() => {
          if (date && sessionNumber) {
            onAdd(formationId, Number(sessionNumber), new Date(date).toISOString(), link || "https://meet.jit.si/LearnEas-" + formationId + "-" + sessionNumber);
            setDate(""); setLink("");
          }
        }}
        className="btn-outline self-start !py-1.5 !text-xs"
      >
        <Video size={14} /> Planifier la séance
      </button>
      <p className="text-xs text-gray-400">
        Si aucun lien n'est saisi, un lien Jitsi Meet gratuit est généré automatiquement.
      </p>
    </div>
  );
}
