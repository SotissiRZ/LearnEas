import Link from "next/link";
import { CalendarClock, Clock3, GraduationCap } from "lucide-react";
import { safePublicGet } from "@/lib/serverPublicApi";
import { MentorshipOffering, Paginated } from "@/types";
import CurrencyPrice from "@/components/ui/CurrencyPrice";
import ApiErrorBanner from "@/components/ui/ApiErrorBanner";

export default async function MentorshipPage() {
  const result = await safePublicGet<Paginated<MentorshipOffering> | MentorshipOffering[]>("/mentorship/offerings/?ordering=price", [], 30);
  const offers = Array.isArray(result.data) ? result.data : result.data.results;
  return (
    <div className="container-app py-10">
      {!result.ok && <ApiErrorBanner message={result.error} />}
      <div className="mb-8 max-w-3xl">
        <span className="badge bg-brand-50 text-brand-700">Mentorat 1:1</span>
        <h1 className="mt-3 text-3xl font-extrabold">Un expert, un créneau, un objectif concret</h1>
        <p className="mt-2 text-gray-500">Réservez une séance privée avec un instructeur KalanPro pour avancer sur un projet, une compétence, un entretien ou votre stratégie professionnelle.</p>
      </div>
      {offers.length === 0 ? <div className="card p-10 text-center text-gray-500">Aucune offre de mentorat publiée pour le moment.</div> : (
        <div className="catalog-grid">
          {offers.map((offer) => <Link key={offer.id} href={`/mentorship/${offer.slug}`} className="card catalog-card group p-5 transition hover:-translate-y-1 hover:shadow-soft">
            <div className="flex items-center gap-3">
              {offer.instructor.avatar ? <img src={offer.instructor.avatar} alt="" loading="lazy" decoding="async" className="h-12 w-12 rounded-full object-cover" /> : <span className="grid h-12 w-12 place-items-center rounded-full bg-brand-50 font-bold text-brand-700"><GraduationCap size={20}/></span>}
              <div className="min-w-0"><p className="truncate font-semibold">{offer.instructor.full_name}</p><p className="truncate text-xs text-gray-500">{offer.instructor.headline || offer.instructor.domain || "Mentor KalanPro"}</p></div>
            </div>
            <h2 className="mt-5 text-lg font-bold group-hover:text-brand-700">{offer.title}</h2>
            <p className="mt-2 line-clamp-3 text-sm leading-6 text-gray-500">{offer.description}</p>
            <div className="mt-4 flex flex-wrap gap-3 text-xs text-gray-500"><span className="flex items-center gap-1"><Clock3 size={14}/>{offer.duration_minutes} min</span><span className="flex items-center gap-1"><CalendarClock size={14}/>{offer.next_slots?.filter(s=>s.is_available).length || 0} créneau(x)</span></div>
            <div className="mt-5 flex items-center justify-between border-t border-gray-100 pt-4"><strong className="text-xl"><CurrencyPrice value={offer.price}/></strong><span className="text-sm font-semibold text-brand-700">Voir les créneaux →</span></div>
          </Link>)}
        </div>
      )}
    </div>
  );
}
