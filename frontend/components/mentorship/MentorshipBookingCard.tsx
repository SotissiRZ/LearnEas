"use client";

import { useMemo, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { CalendarClock, CheckCircle2, Loader2, ShoppingCart, Video } from "lucide-react";
import { MentorshipBooking, MentorshipOffering } from "@/types";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { useCart } from "@/hooks/useCart";
import CurrencyPrice from "@/components/ui/CurrencyPrice";

export default function MentorshipBookingCard({ offering }: { offering: MentorshipOffering }) {
  const { user, hydrated } = useAuth();
  const addMentorshipBooking = useCart((s) => s.addMentorshipBooking);
  const router = useRouter();
  const pathname = usePathname();
  const available = useMemo(() => (offering.next_slots || []).filter((s) => s.is_available), [offering.next_slots]);
  const [slotId, setSlotId] = useState<number | null>(available[0]?.id ?? null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function reserve() {
    if (!hydrated) return;
    if (!user) {
      router.push(`/login?next=${encodeURIComponent(pathname)}`);
      return;
    }
    if (!slotId) {
      setError("Choisissez un créneau disponible.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const booking = await api.post<MentorshipBooking>("/mentorship/bookings/", { slot_id: slotId, learner_note: note });
      if (booking.status === "confirmed") {
        router.push("/dashboard/student/mentorship?booked=1");
        return;
      }
      addMentorshipBooking(booking);
      router.push("/checkout");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Impossible de réserver ce créneau.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <aside className="card sticky top-24 p-5">
      <div className="flex items-baseline justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Séance individuelle</p>
          <p className="mt-1 text-3xl font-extrabold"><CurrencyPrice value={offering.price} /></p>
        </div>
        <span className="badge bg-brand-50 text-brand-700">{offering.duration_minutes} min</span>
      </div>

      <div className="mt-5 space-y-2 text-sm text-gray-600">
        <p className="flex items-center gap-2"><Video size={16} /> Visioconférence privée LearnEas</p>
        <p className="flex items-center gap-2"><CalendarClock size={16} /> Réservation au moins {offering.booking_notice_hours} h à l'avance</p>
        <p className="flex items-center gap-2"><CheckCircle2 size={16} /> Annulation apprenant au moins {offering.cancellation_notice_hours} h avant</p>
      </div>

      <label className="mt-5 block text-sm font-semibold">Créneau</label>
      {available.length ? (
        <select value={slotId ?? ""} onChange={(e) => setSlotId(Number(e.target.value))} className="input-admin mt-1 w-full">
          {available.map((slot) => (
            <option key={slot.id} value={slot.id}>
              {new Date(slot.starts_at).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short" })}
            </option>
          ))}
        </select>
      ) : (
        <div className="mt-1 rounded-xl bg-amber-50 p-3 text-sm text-amber-800">Aucun créneau réservable pour le moment.</div>
      )}

      <label className="mt-4 block text-sm font-semibold">Votre objectif <span className="font-normal text-gray-400">(facultatif)</span></label>
      <textarea value={note} onChange={(e) => setNote(e.target.value)} maxLength={1200} rows={3} className="input-admin mt-1 w-full" placeholder="Ex : préparer un entretien, débloquer un projet, revoir mon portfolio…" />

      {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
      <button disabled={busy || !available.length} onClick={reserve} className="btn-primary mt-5 w-full disabled:cursor-not-allowed disabled:opacity-50">
        {busy ? <Loader2 size={17} className="animate-spin" /> : <ShoppingCart size={17} />}
        {Number(offering.price) > 0 ? "Réserver et payer" : "Réserver gratuitement"}
      </button>
      <p className="mt-2 text-center text-[11px] leading-5 text-gray-400">Pour une séance payante, le créneau est réservé 45 minutes pendant le paiement.</p>
    </aside>
  );
}
