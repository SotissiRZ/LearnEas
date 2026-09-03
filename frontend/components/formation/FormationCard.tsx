import Link from "next/link";
import { Users, CalendarDays, Video, Clock } from "lucide-react";
import { InteractiveFormation } from "@/types";
import CurrencyPrice from "@/components/ui/CurrencyPrice";
import LevelBadge from "@/components/ui/LevelBadge";
import QuickAddButton from "@/components/course/QuickAddButton";

export default function FormationCard({ formation }: { formation: InteractiveFormation }) {
  return (
    <Link
      href={`/formations/${formation.slug}`}
      className="card group flex flex-col overflow-hidden transition hover:-translate-y-1 hover:shadow-soft"
    >
      <div className="relative flex aspect-video w-full items-center justify-center overflow-hidden bg-gradient-to-br from-violet-100 to-brand-50">
        {formation.thumbnail ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img loading="lazy" decoding="async" src={formation.thumbnail} alt={formation.title} className="h-full w-full object-cover" />
        ) : (
          <Video size={44} className="text-violet-300" />
        )}
        <span className="badge absolute left-3 top-3 bg-white/95 text-violet-700 shadow">En direct</span>
        {formation.is_full && (
          <span className="badge absolute right-3 top-3 bg-rose-600 text-white">Complet</span>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-2 p-4">
        <div className="flex items-center gap-2">
          <LevelBadge level={formation.level} />
          {formation.category && <span className="text-xs font-medium text-gray-400">{formation.category.name}</span>}
        </div>

        <h3 className="line-clamp-2 text-base font-bold leading-snug text-ink group-hover:text-brand-700">
          {formation.title}
        </h3>
        <p className="text-xs font-medium text-gray-500">
          {formation.instructor?.full_name}
          {formation.co_instructor ? ` & ${formation.co_instructor.full_name}` : ""}
        </p>

        <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-gray-500">
          <span className="flex items-center gap-1"><Video size={14} /> {formation.num_sessions} séances</span>
          <span className="flex items-center gap-1"><Clock size={14} /> {formation.session_duration_minutes} min/séance</span>
          <span className="flex items-center gap-1"><Users size={14} /> {formation.seats_left} places restantes</span>
        </div>
        {formation.start_date && (
          <span className="flex items-center gap-1 text-xs text-gray-500">
            <CalendarDays size={14} /> Début le {new Date(formation.start_date).toLocaleDateString("fr-FR")}
          </span>
        )}

        <div className="mt-auto flex items-center justify-between gap-2 pt-2">
          <span className="text-lg font-extrabold text-ink"><CurrencyPrice value={formation.price} /></span>
          <QuickAddButton item={{ kind: "formation", data: formation }} />
        </div>
      </div>
    </Link>
  );
}
