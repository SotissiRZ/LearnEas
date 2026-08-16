import { notFound } from "next/navigation";
import { CalendarDays, Clock, Users, Video, Lock, ExternalLink, CheckCircle2 } from "lucide-react";
import { api, formatPrice } from "@/lib/api";
import { InteractiveFormation } from "@/types";
import LevelBadge from "@/components/ui/LevelBadge";
import { AddFormationToCartButton } from "@/components/formation/AddFormationToCartButton";

async function getFormation(slug: string): Promise<InteractiveFormation | null> {
  try {
    return await api.get<InteractiveFormation>(`/formations/${slug}/`);
  } catch {
    return null;
  }
}

export default async function FormationDetailPage({ params }: { params: { slug: string } }) {
  const formation = await getFormation(params.slug);
  if (!formation) notFound();

  return (
    <div className="container-app grid grid-cols-1 gap-10 py-10 lg:grid-cols-[1fr_380px]">
      <div className="flex flex-col gap-8">
        <div>
          <span className="badge bg-violet-50 text-violet-700">Formation interactive en direct</span>
          <h1 className="mt-2 text-3xl font-extrabold">{formation.title}</h1>
          <div className="mt-3 flex flex-wrap items-center gap-4 text-sm">
            <LevelBadge level={formation.level} />
            <span className="flex items-center gap-1 text-gray-500"><Users size={16} /> {formation.students_count} inscrit(s) — {formation.seats_left} places restantes</span>
          </div>
          <p className="mt-2 text-sm text-gray-500">
            Animée par <span className="font-semibold">{formation.instructor.full_name}</span>
            {formation.co_instructor && <> et <span className="font-semibold">{formation.co_instructor.full_name}</span></>}
          </p>
        </div>

        <div className="card p-6">
          <h2 className="mb-3 text-xl font-bold">Description</h2>
          <p className="whitespace-pre-line text-sm leading-relaxed text-gray-600">{formation.description}</p>
        </div>

        <div className="card p-6">
          <h2 className="mb-4 text-xl font-bold">Planning des séances</h2>
          <div className="flex flex-col gap-3">
            {(formation.sessions || []).map((s) => (
              <div key={s.id} className="flex flex-wrap items-center gap-3 rounded-lg border border-gray-100 p-3 text-sm">
                <span className="badge bg-brand-50 text-brand-700">Séance {s.session_number}</span>
                <span className="flex items-center gap-1 text-gray-600">
                  <CalendarDays size={14} /> {new Date(s.scheduled_at).toLocaleString("fr-FR", { dateStyle: "long", timeStyle: "short" })}
                </span>
                <span className="flex items-center gap-1 text-gray-500"><Clock size={14} /> {s.duration_minutes} min</span>
                <span className="ml-auto">
                  {s.meeting_link ? (
                    <a href={s.meeting_link} target="_blank" rel="noreferrer" className="flex items-center gap-1 font-semibold text-brand-700">
                      <Video size={14} /> Rejoindre <ExternalLink size={12} />
                    </a>
                  ) : (
                    <span className="flex items-center gap-1 text-gray-400"><Lock size={14} /> Réservé aux inscrits</span>
                  )}
                </span>
              </div>
            ))}
            {(!formation.sessions || formation.sessions.length === 0) && (
              <p className="text-sm text-gray-500">Le planning détaillé sera communiqué après inscription.</p>
            )}
          </div>
        </div>
      </div>

      <div>
        <div className="card sticky top-24 overflow-hidden">
          <div className="flex aspect-video w-full items-center justify-center bg-gradient-to-br from-violet-100 to-brand-50">
            {formation.thumbnail ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={formation.thumbnail} alt={formation.title} className="h-full w-full object-cover" />
            ) : (
              <Video size={48} className="text-violet-300" />
            )}
          </div>
          <div className="p-5">
            <span className="text-3xl font-extrabold">{formatPrice(formation.price)}</span>

            <div className="mt-4">
              {formation.is_enrolled ? (
                <div className="flex items-center gap-2 rounded-lg bg-brand-50 p-3 text-sm font-semibold text-brand-700">
                  <CheckCircle2 size={18} /> Vous êtes inscrit — rejoignez les séances ci-contre.
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
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
