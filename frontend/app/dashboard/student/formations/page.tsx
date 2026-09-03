"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Video, Calendar, Users, Lock } from "lucide-react";
import { api } from "@/lib/api";
import { FormationEnrollment, InteractiveFormation } from "@/types";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import DashboardNav from "@/components/dashboard/DashboardNav";
import GuardScreen from "@/components/ui/GuardScreen";

export default function StudentFormationsPage() {
  const { ready } = useAuthGuard();
  const [enrollments, setEnrollments] = useState<FormationEnrollment[]>([]);
  const [details, setDetails] = useState<Record<string, InteractiveFormation>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ready) return;
    api.get<{ results: FormationEnrollment[] } | FormationEnrollment[]>("/my-formations/")
      .then(async (data: any) => {
        const list: FormationEnrollment[] = data.results || data;
        setEnrollments(list);
        // On récupère le détail (avec les liens de séance débloqués) pour chaque formation
        const entries = await Promise.all(
          list.map(async (e) => {
            const full = await api.get<InteractiveFormation>(`/formations/${e.formation.slug}/`);
            return [e.formation.slug, full] as const;
          })
        );
        setDetails(Object.fromEntries(entries));
      })
      .finally(() => setLoading(false));
  }, [ready]);

  if (!ready) return <GuardScreen />;

  return (
    <div className="container-app py-10">
      <DashboardNav role="student" />
      <h2 className="mb-4 text-xl font-bold">Mes cohortes live</h2>

      {loading ? (
        <p className="text-gray-500">Chargement...</p>
      ) : enrollments.length === 0 ? (
        <div className="card p-10 text-center text-gray-500">
          Aucune cohorte live. <Link href="/formations" className="font-semibold text-brand-700">Explorer le catalogue</Link>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {enrollments.map((e) => {
            const full = details[e.formation.slug];
            return (
              <div key={e.id} className="card p-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-bold">{e.formation.title}</p>
                    <p className="text-xs text-gray-500">
                      <Users size={12} className="inline" /> {e.formation.instructor.full_name} ·{" "}
                      {e.formation.num_sessions} séances
                    </p>
                  </div>
                  {e.certificate_issued && (
                    <span className="badge bg-brand-50 text-brand-700">Certifiée</span>
                  )}
                </div>

                <div className="mt-4 flex flex-col gap-2 border-t border-gray-100 pt-4">
                  {(full?.sessions || []).map((s) => (
                    <div key={s.id} className="flex flex-wrap items-center gap-3 rounded-lg border border-gray-100 p-3 text-sm">
                      <span className="badge bg-brand-50 text-brand-700">Séance {s.session_number}</span>
                      <span className="flex items-center gap-1 text-gray-600">
                        <Calendar size={14} />
                        {new Date(s.scheduled_at).toLocaleString("fr-FR", { dateStyle: "long", timeStyle: "short" })}
                      </span>
                      <span className="ml-auto">
                        {s.can_join ? (
                          <Link href={`/live/session/${s.id}`} className="flex items-center gap-1 font-semibold text-brand-700">
                            <Video size={14} /> Rejoindre sur LearnEas
                          </Link>
                        ) : (
                          <span className="flex items-center gap-1 text-gray-400"><Lock size={14} /> Salle indisponible</span>
                        )}
                      </span>
                    </div>
                  ))}
                  {(!full?.sessions || full.sessions.length === 0) && (
                    <p className="text-sm text-gray-500">Le planning sera communiqué prochainement par l'instructeur.</p>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
