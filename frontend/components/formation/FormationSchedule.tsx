"use client";

import { CalendarDays, Clock, Lock, Video } from "lucide-react";
import { InteractiveFormation } from "@/types";
import { useAuthenticatedResource } from "@/hooks/useAuthenticatedResource";

export default function FormationSchedule({ initialFormation }: { initialFormation: InteractiveFormation }) {
  const formation = useAuthenticatedResource<InteractiveFormation>(`/formations/${initialFormation.slug}/`, initialFormation);
  return (
    <div className="flex flex-col gap-3">
      {(formation.sessions || []).map((s) => (
        <div key={s.id} className="flex flex-wrap items-center gap-3 rounded-lg border border-gray-100 p-3 text-sm">
          <span className="badge bg-brand-50 text-brand-700">Séance {s.session_number}</span>
          <span className="flex items-center gap-1 text-gray-600">
            <CalendarDays size={14} /> {new Date(s.scheduled_at).toLocaleString("fr-FR", { dateStyle: "long", timeStyle: "short" })}
          </span>
          <span className="flex items-center gap-1 text-gray-500"><Clock size={14} /> {s.duration_minutes} min</span>
          <span className="ml-auto">
            {s.can_join ? (
              <a href={`/live/session/${s.id}`} className="flex items-center gap-1 font-semibold text-brand-700">
                <Video size={14} /> Rejoindre sur LearnEas
              </a>
            ) : (
              <span className="flex items-center gap-1 text-gray-400"><Lock size={14} /> {formation.is_enrolled ? "En attente du démarrage" : "Réservé aux inscrits"}</span>
            )}
          </span>
        </div>
      ))}
      {(!formation.sessions || formation.sessions.length === 0) && (
        <p className="text-sm text-gray-500">Le planning détaillé sera communiqué après inscription.</p>
      )}
    </div>
  );
}
