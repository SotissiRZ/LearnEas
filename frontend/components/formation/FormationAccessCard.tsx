"use client";

import { useState } from "react";
import { CheckCircle2, Clock, Hourglass, Loader2, Users, Video } from "lucide-react";
import { InteractiveFormation } from "@/types";
import CurrencyPrice from "@/components/ui/CurrencyPrice";
import { useAuthenticatedResource } from "@/hooks/useAuthenticatedResource";
import { AddFormationToCartButton } from "@/components/formation/AddFormationToCartButton";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { usePathname, useRouter } from "next/navigation";

export default function FormationAccessCard({ initialFormation }: { initialFormation: InteractiveFormation }) {
  const remote = useAuthenticatedResource<InteractiveFormation>(`/formations/${initialFormation.slug}/`, initialFormation);
  const [localFormation, setLocalFormation] = useState<InteractiveFormation | null>(null);
  const formation = localFormation || remote;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const { user, hydrated } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  async function reload() {
    const next = await api.get<InteractiveFormation>(`/formations/${initialFormation.slug}/`);
    setLocalFormation(next);
  }

  async function waitlist(action: "join_waitlist" | "leave_waitlist") {
    if (!hydrated) return;
    if (!user) {
      router.push(`/login?next=${encodeURIComponent(pathname)}`);
      return;
    }
    setBusy(true); setError("");
    try {
      await api.post(`/formations/${formation.slug}/${action}/`, {});
      await reload();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Action impossible sur la liste d'attente.");
    } finally { setBusy(false); }
  }

  const waiting = formation.waitlist_status === "waiting";
  const offered = formation.waitlist_status === "offered";
  const checkoutAvailable = formation.can_checkout ?? (!formation.is_full && Boolean(formation.is_enrollment_open));

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
        <div className="mt-4 space-y-2">
          {formation.is_enrolled ? (
            <div className="flex items-center gap-2 rounded-lg bg-brand-50 p-3 text-sm font-semibold text-brand-700">
              <CheckCircle2 size={18} /> Vous êtes inscrit · rejoignez les séances ci-contre.
            </div>
          ) : offered ? (
            <>
              <div className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">
                <p className="font-semibold">Une place vous est réservée temporairement.</p>
                {formation.waitlist_offer_expires_at && <p className="mt-1 text-xs">Priorité jusqu'au {new Date(formation.waitlist_offer_expires_at).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short" })}.</p>}
              </div>
              <AddFormationToCartButton formation={formation} />
              <button disabled={busy} onClick={() => waitlist("leave_waitlist")} className="btn-outline w-full !py-2 text-xs">Libérer ma priorité</button>
            </>
          ) : checkoutAvailable ? (
            <AddFormationToCartButton formation={formation} />
          ) : waiting ? (
            <div className="rounded-lg border border-amber-100 bg-amber-50 p-3 text-sm text-amber-800">
              <p className="flex items-center gap-2 font-semibold"><Hourglass size={16}/> Liste d'attente</p>
              <p className="mt-1 text-xs">Position actuelle : {formation.waitlist_position ?? "—"}. Vous serez prioritaire lorsqu'une place se libère.</p>
              <button disabled={busy} onClick={() => waitlist("leave_waitlist")} className="btn-outline mt-3 w-full !py-2 text-xs">Quitter la liste</button>
            </div>
          ) : formation.is_waitlist_open ? (
            <button disabled={busy} onClick={() => waitlist("join_waitlist")} className="btn-primary w-full">
              {busy ? <Loader2 size={16} className="animate-spin"/> : <Hourglass size={16}/>} Rejoindre la liste d'attente
            </button>
          ) : (
            <button disabled className="btn-outline w-full cursor-not-allowed opacity-60">Inscriptions closes</button>
          )}
          {error && <p className="text-xs text-red-600">{error}</p>}
        </div>
        <div className="mt-5 flex flex-col gap-2 border-t border-gray-100 pt-4 text-sm text-gray-600">
          <span className="flex items-center gap-2"><Video size={16} /> {formation.num_sessions} séances en direct</span>
          <span className="flex items-center gap-2"><Clock size={16} /> {formation.session_duration_minutes} min par séance</span>
          <span className="flex items-center gap-2"><Users size={16} /> {formation.effective_seats_left ?? formation.seats_left} place(s) actuellement disponible(s)</span>
          {formation.min_students && formation.min_students > 1 && <span className="text-xs text-gray-500">Démarrage prévu à partir de {formation.min_students} participants.</span>}
          {formation.enrollment_deadline && <span className="text-xs text-gray-500">Clôture des inscriptions : {new Date(formation.enrollment_deadline).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short" })}</span>}
        </div>
      </div>
    </div>
  );
}
