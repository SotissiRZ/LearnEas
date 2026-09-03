"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CalendarClock, CheckCircle2, Clock3, Loader2, Video, XCircle } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { MentorshipBooking, Paginated } from "@/types";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import DashboardNav from "@/components/dashboard/DashboardNav";
import GuardScreen from "@/components/ui/GuardScreen";
import CurrencyPrice from "@/components/ui/CurrencyPrice";
import { useCart } from "@/hooks/useCart";

export default function StudentMentorshipPage() {
  const { ready } = useAuthGuard();
  const [rows, setRows] = useState<MentorshipBooking[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const addMentorshipBooking = useCart((state) => state.addMentorshipBooking);

  async function load() {
    setLoading(true);
    try {
      const data = await api.get<Paginated<MentorshipBooking> | MentorshipBooking[]>("/mentorship/bookings/?ordering=-created_at");
      setRows(Array.isArray(data) ? data : data.results);
    } catch (e) { setError(e instanceof ApiError ? e.message : "Impossible de charger vos rendez-vous."); }
    finally { setLoading(false); }
  }
  useEffect(() => { if (ready) load(); }, [ready]);

  async function cancel(id: number) {
    if (!confirm("Annuler ce rendez-vous ? Un paiement déjà effectué n'est pas remboursé automatiquement.")) return;
    try { await api.post(`/mentorship/bookings/${id}/cancel/`, {}); await load(); }
    catch (e) { setError(e instanceof ApiError ? e.message : "Annulation impossible."); }
  }

  function resumePayment(booking: MentorshipBooking) {
    addMentorshipBooking(booking);
    window.location.href = "/checkout";
  }

  if (!ready) return <GuardScreen />;
  return <div className="container-app py-10">
    <DashboardNav role="student" />
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3"><div><h1 className="text-xl font-bold">Mes rendez-vous de mentorat</h1><p className="mt-1 text-sm text-gray-500">Séances individuelles réservées avec vos mentors.</p></div><Link href="/mentorship" className="btn-primary !py-2 !text-sm">Trouver un mentor</Link></div>
    {error && <div className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</div>}
    {loading ? <div className="card p-10 text-center text-gray-400"><Loader2 className="mx-auto mb-2 animate-spin"/>Chargement...</div> : rows.length === 0 ? <div className="card p-10 text-center text-gray-500">Aucun rendez-vous. <Link href="/mentorship" className="font-semibold text-brand-700">Découvrir les mentors</Link></div> : <div className="space-y-4">
      {rows.map((b) => <article key={b.id} className="card p-5"><div className="flex flex-wrap items-start justify-between gap-4"><div><div className="flex flex-wrap items-center gap-2"><h2 className="font-bold">{b.offering.title}</h2><Status status={b.status}/></div><p className="mt-1 text-sm text-gray-500">avec {b.mentor_name}</p><div className="mt-3 flex flex-wrap gap-4 text-xs text-gray-500"><span className="flex items-center gap-1"><CalendarClock size={14}/>{new Date(b.slot.starts_at).toLocaleString("fr-FR",{dateStyle:"long",timeStyle:"short"})}</span><span className="flex items-center gap-1"><Clock3 size={14}/>{b.slot.duration_minutes} min</span><span><CurrencyPrice value={b.price_snapshot}/></span></div></div><div className="flex flex-wrap gap-2">{b.status === "pending_payment" && <button type="button" onClick={()=>resumePayment(b)} className="btn-primary !py-2 !text-xs">Finaliser le paiement</button>}{b.status === "confirmed" && b.join_session_id && <Link href={`/live/session/${b.join_session_id}`} className="btn-primary !py-2 !text-xs"><Video size={14}/> Ouvrir la salle</Link>}{["pending_payment","confirmed"].includes(b.status) && <button onClick={()=>cancel(b.id)} className="btn-outline !py-2 !text-xs"><XCircle size={14}/> Annuler</button>}</div></div>{b.learner_note && <p className="mt-4 rounded-xl bg-gray-50 p-3 text-xs leading-5 text-gray-600"><strong>Votre objectif :</strong> {b.learner_note}</p>}{b.mentor_note && <p className="mt-3 rounded-xl bg-brand-50 p-3 text-xs leading-5 text-brand-800"><strong>Note du mentor :</strong> {b.mentor_note}</p>}</article>)}
    </div>}
  </div>;
}

function Status({status}:{status:MentorshipBooking["status"]}) { const map:any={pending_payment:["Paiement en attente","bg-amber-50 text-amber-700"],confirmed:["Confirmée","bg-emerald-50 text-emerald-700"],completed:["Terminée","bg-blue-50 text-blue-700"],cancelled:["Annulée","bg-gray-100 text-gray-600"],expired:["Expirée","bg-red-50 text-red-700"]}; const [label,cls]=map[status]; return <span className={`badge ${cls}`}>{status==="confirmed"?<CheckCircle2 size={12}/>:null}{label}</span> }
