"use client";

import { CheckCircle2, Clock, Users, Video } from "lucide-react";
import { InteractiveFormation } from "@/types";
import CurrencyPrice from "@/components/ui/CurrencyPrice";
import { useAuthenticatedResource } from "@/hooks/useAuthenticatedResource";
import { AddFormationToCartButton } from "@/components/formation/AddFormationToCartButton";

export default function FormationAccessCard({ initialFormation }: { initialFormation: InteractiveFormation }) {
  const formation = useAuthenticatedResource<InteractiveFormation>(`/formations/${initialFormation.slug}/`, initialFormation);
  return (
    <div className="card sticky top-24 overflow-hidden">
      <div className="flex aspect-video w-full items-center justify-center bg-gradient-to-br from-violet-100 to-brand-50">
        {formation.thumbnail ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img loading="lazy" decoding="async" src={formation.thumbnail} alt={formation.title} className="h-full w-full object-cover" />
        ) : (
          <Video size={48} className="text-violet-300" />
        )}
      </div>
      <div className="p-5">
        <span className="text-3xl font-extrabold"><CurrencyPrice value={formation.price} /></span>
        <div className="mt-4">
          {formation.is_enrolled ? (
            <div className="flex items-center gap-2 rounded-lg bg-brand-50 p-3 text-sm font-semibold text-brand-700">
              <CheckCircle2 size={18} /> Vous êtes inscrit · rejoignez les séances ci-contre.
            </div>
          ) : formation.is_full ? (
            <button disabled className="btn-outline w-full cursor-not-allowed opacity-60">Complet</button>
          ) : (
            <AddFormationToCartButton formation={formation} />
          )}
        </div>
        <div className="mt-5 flex flex-col gap-2 border-t border-gray-100 pt-4 text-sm text-gray-600">
          <span className="flex items-center gap-2"><Video size={16} /> {formation.num_sessions} séances en direct</span>
          <span className="flex items-center gap-2"><Clock size={16} /> {formation.session_duration_minutes} min par séance</span>
          <span className="flex items-center gap-2"><Users size={16} /> Groupe limité à {formation.max_students} apprenants</span>
          {formation.min_students && formation.min_students > 1 && <span className="text-xs text-gray-500">Démarrage prévu à partir de {formation.min_students} participants.</span>}
          {formation.enrollment_deadline && <span className="text-xs text-gray-500">Clôture des inscriptions : {new Date(formation.enrollment_deadline).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short" })}</span>}
        </div>
      </div>
    </div>
  );
}
