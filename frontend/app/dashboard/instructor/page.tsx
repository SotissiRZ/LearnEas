"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BookOpen, FileText, Users, Star, PlusCircle, WalletCards, Banknote, Save, ArrowDownToLine } from "lucide-react";
import { api, ApiError, formatPrice } from "@/lib/api";
import { Course, PDFProduct } from "@/types";
import { useAuth } from "@/hooks/useAuth";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import DashboardNav from "@/components/dashboard/DashboardNav";
import GuardScreen from "@/components/ui/GuardScreen";

interface FinanceSummary {
  gross_revenue: string; total_earnings: string; available_balance: string; paid_out: string;
  sales_count: number; commission_percent: number; minimum_payout: string; payout_profile_configured: boolean;
  recent_sales: { id: number; title: string; type: string; gross: string; earning: string; paid_at: string }[];
}
interface PayoutProfile { method: "bank" | "mobile_money" | "paypal"; account_name: string; account_reference: string; }
interface Payout { id: number; amount: string; status: string; requested_at: string; method: string; }

export default function InstructorDashboard() {
  const { ready } = useAuthGuard();
  const { user } = useAuth();
  const [courses, setCourses] = useState<Course[]>([]);
  const [pdfs, setPdfs] = useState<PDFProduct[]>([]);
  const [finance, setFinance] = useState<FinanceSummary | null>(null);
  const [profile, setProfile] = useState<PayoutProfile>({ method: "bank", account_name: "", account_reference: "" });
  const [payouts, setPayouts] = useState<Payout[]>([]);
  const [withdrawAmount, setWithdrawAmount] = useState("");
  const [message, setMessage] = useState("");

  async function loadFinance() {
    const [f, p, po] = await Promise.all([
      api.get<FinanceSummary>("/payments/instructor/finance/"),
      api.get<PayoutProfile>("/payments/instructor/payout-profile/"),
      api.get<{ results: Payout[] } | Payout[]>("/payments/payouts/"),
    ]);
    setFinance(f); setProfile(p); setPayouts((po as any).results || po);
  }

  useEffect(() => {
    if (!ready || !user || !["instructor", "admin"].includes(user.role)) return;
    api.get<{ results: Course[] } | Course[]>("/catalog/courses/my_courses/").then((d: any) => setCourses(d.results || d)).catch(() => {});
    api.get<{ results: PDFProduct[] } | PDFProduct[]>("/catalog/pdfs/my_pdfs/").then((d: any) => setPdfs(d.results || d)).catch(() => {});
    loadFinance().catch(() => {});
  }, [ready, user]);

  if (!ready) return <GuardScreen />;
  if (user && user.role !== "instructor" && user.role !== "admin") return <BecomeInstructor />;

  const totalStudents = courses.reduce((sum, c) => sum + c.students_count, 0);
  const avgRating = courses.length ? (courses.reduce((sum, c) => sum + parseFloat(c.rating_avg), 0) / courses.length).toFixed(1) : "0.0";

  async function saveProfile() {
    setMessage("");
    try { setProfile(await api.patch<PayoutProfile>("/payments/instructor/payout-profile/", profile)); setMessage("Méthode de versement enregistrée."); }
    catch (e) { setMessage(e instanceof ApiError ? e.message : "Impossible d'enregistrer la méthode de versement."); }
  }
  async function requestPayout() {
    setMessage("");
    try { await api.post("/payments/payouts/", { amount: Number(withdrawAmount) }); setWithdrawAmount(""); await loadFinance(); setMessage("Demande de versement envoyée à l'administration."); }
    catch (e) { setMessage(e instanceof ApiError ? e.message : "Impossible de demander le versement."); }
  }

  return <div className="container-app py-10">
    <DashboardNav role="instructor" />
    <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-3 xl:grid-cols-6">
      <Stat icon={<BookOpen size={20} />} label="Cours" value={courses.length} />
      <Stat icon={<FileText size={20} />} label="PDF" value={pdfs.length} />
      <Stat icon={<Users size={20} />} label="Étudiants" value={totalStudents} />
      <Stat icon={<Star size={20} />} label="Note moyenne" value={avgRating} />
      <Stat icon={<WalletCards size={20} />} label="Gains disponibles" value={formatPrice(finance?.available_balance || 0)} />
      <Stat icon={<Banknote size={20} />} label="Déjà versé" value={formatPrice(finance?.paid_out || 0)} />
    </div>

    <div className="mb-8 grid grid-cols-1 gap-6 lg:grid-cols-[1.2fr_.8fr]">
      <div className="card p-5">
        <div className="mb-4 flex items-center justify-between"><div><h2 className="font-bold">Revenus instructeur</h2><p className="text-xs text-gray-500">Commission plateforme : {finance?.commission_percent ?? 15}% · {finance?.sales_count ?? 0} vente(s)</p></div><span className="text-xl font-extrabold">{formatPrice(finance?.total_earnings || 0)}</span></div>
        <div className="overflow-hidden rounded-xl border border-gray-100">
          <table className="w-full text-sm"><thead className="bg-gray-50 text-left text-xs text-gray-500"><tr><th className="px-3 py-2">Vente</th><th className="px-3 py-2">Brut</th><th className="px-3 py-2">Votre part</th></tr></thead><tbody className="divide-y divide-gray-100">{(finance?.recent_sales || []).map((sale) => <tr key={sale.id}><td className="px-3 py-2">{sale.title}</td><td className="px-3 py-2">{formatPrice(sale.gross)}</td><td className="px-3 py-2 font-semibold text-brand-700">{formatPrice(sale.earning)}</td></tr>)}{!finance?.recent_sales?.length && <tr><td colSpan={3} className="px-3 py-6 text-center text-gray-400">Aucune vente payée.</td></tr>}</tbody></table>
        </div>
      </div>

      <div className="card p-5">
        <h2 className="font-bold">Recevoir mon argent</h2><p className="mb-4 text-xs text-gray-500">Configurez votre destination, puis demandez un versement. Le minimum est {formatPrice(finance?.minimum_payout || 100)}.</p>
        <div className="flex flex-col gap-3">
          <select value={profile.method} onChange={(e) => setProfile({ ...profile, method: e.target.value as PayoutProfile["method"] })} className="rounded-lg border border-gray-200 px-3 py-2 text-sm"><option value="bank">Virement bancaire</option><option value="mobile_money">Mobile Money</option><option value="paypal">PayPal</option></select>
          <input value={profile.account_name} onChange={(e) => setProfile({ ...profile, account_name: e.target.value })} placeholder="Nom du titulaire" className="rounded-lg border border-gray-200 px-3 py-2 text-sm" />
          <input value={profile.account_reference} onChange={(e) => setProfile({ ...profile, account_reference: e.target.value })} placeholder={profile.method === "bank" ? "IBAN / RIB" : profile.method === "paypal" ? "Email PayPal" : "Numéro Mobile Money"} className="rounded-lg border border-gray-200 px-3 py-2 text-sm" />
          <button onClick={saveProfile} className="btn-outline !py-2 !text-xs"><Save size={14} /> Enregistrer</button>
          <div className="mt-1 flex gap-2 border-t border-gray-100 pt-3"><input type="number" min={0} value={withdrawAmount} onChange={(e) => setWithdrawAmount(e.target.value)} placeholder="Montant MAD" className="min-w-0 flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm" /><button onClick={requestPayout} className="btn-primary !px-3 !py-2 !text-xs"><ArrowDownToLine size={14} /> Retirer</button></div>
          {message && <p className="text-xs text-gray-600">{message}</p>}
        </div>
      </div>
    </div>

    <div className="card mb-8 p-5">
      <div className="mb-3 flex items-center justify-between"><div><h2 className="font-bold">Historique des versements</h2><p className="text-xs text-gray-500">Suivez chaque demande jusqu'à sa validation par l'administration.</p></div></div>
      <div className="overflow-x-auto"><table className="w-full text-sm"><thead className="bg-gray-50 text-left text-xs text-gray-500"><tr><th className="px-3 py-2">Date</th><th className="px-3 py-2">Méthode</th><th className="px-3 py-2">Montant</th><th className="px-3 py-2">Statut</th></tr></thead><tbody className="divide-y divide-gray-100">{payouts.slice(0, 8).map((p) => <tr key={p.id}><td className="px-3 py-2 text-gray-500">{new Date(p.requested_at).toLocaleDateString("fr-FR")}</td><td className="px-3 py-2">{p.method}</td><td className="px-3 py-2 font-semibold">{formatPrice(p.amount)}</td><td className="px-3 py-2"><span className={`badge ${p.status === "paid" ? "bg-emerald-50 text-emerald-700" : p.status === "failed" ? "bg-red-50 text-red-700" : "bg-amber-50 text-amber-700"}`}>{p.status}</span></td></tr>)}{payouts.length === 0 && <tr><td colSpan={4} className="px-3 py-5 text-center text-gray-400">Aucune demande de versement.</td></tr>}</tbody></table></div>
    </div>

    <div className="mb-4 flex items-center justify-between"><h2 className="text-xl font-bold">Mes cours récents</h2><Link href="/dashboard/instructor/courses/new" className="btn-primary !py-2 !text-sm"><PlusCircle size={16} /> Nouveau cours</Link></div>
    {courses.length === 0 ? <p className="mb-8 text-gray-500">Aucun cours pour le moment.</p> : <div className="mb-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">{courses.slice(0, 6).map((c) => <Link key={c.id} href={`/dashboard/instructor/courses/${c.id}`} className="card p-4 transition hover:-translate-y-1 hover:shadow-soft"><p className="line-clamp-2 font-semibold">{c.title}</p><p className="mt-1 text-xs text-gray-500">{c.total_lessons} vidéos · {c.students_count} étudiants</p><span className={`badge mt-2 ${c.published ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-600"}`}>{c.published ? "Publié" : "Brouillon"}</span></Link>)}</div>}
  </div>;
}

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: number | string }) { return <div className="card flex items-center gap-3 p-4"><div className="grid h-11 w-11 place-items-center rounded-xl bg-brand-50 text-brand-600">{icon}</div><div><p className="text-xl font-extrabold">{value}</p><p className="text-xs text-gray-500">{label}</p></div></div>; }

function BecomeInstructor() {
  const [form, setForm] = useState({ domain: "", years_experience: "0", headline: "", message: "" });
  const [application, setApplication] = useState<{ status: string; review_note?: string; domain?: string; created_at?: string } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<{ status: string; review_note?: string; domain?: string; created_at?: string }>("/auth/become-instructor/")
      .then(setApplication)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Impossible de charger l'état de la demande."))
      .finally(() => setLoading(false));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true); setError("");
    try {
      const result = await api.post<{ status: string; review_note?: string; domain?: string; created_at?: string }>("/auth/become-instructor/", form);
      setApplication(result);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Impossible d'envoyer la demande.");
    } finally {
      setLoading(false);
    }
  }

  if (loading && !application) return <GuardScreen />;

  if (application?.status === "pending") {
    return <div className="container-app flex min-h-[60vh] items-center justify-center py-16"><div className="card w-full max-w-lg p-8"><span className="badge bg-amber-50 text-amber-700">En attente de validation</span><h1 className="mt-4 text-2xl font-extrabold">Votre demande instructeur a été envoyée</h1><p className="mt-2 text-sm leading-6 text-gray-500">Un administrateur doit maintenant vérifier votre profil avant d'activer les fonctionnalités de publication et de paiement instructeur.</p>{application.domain && <p className="mt-4 rounded-xl bg-gray-50 p-3 text-sm"><b>Domaine :</b> {application.domain}</p>}</div></div>;
  }

  return <div className="container-app flex min-h-[60vh] items-center justify-center py-16"><form onSubmit={handleSubmit} className="card w-full max-w-md p-8"><h1 className="mb-1 text-2xl font-extrabold">Devenir instructeur</h1><p className="mb-6 text-sm text-gray-500">Envoyez votre demande. L'administration la valide avant l'ouverture de votre espace instructeur.</p>{application?.status === "rejected" && <div className="mb-4 rounded-xl border border-red-100 bg-red-50 p-3 text-sm text-red-700">Votre précédente demande a été refusée.{application.review_note ? ` Motif : ${application.review_note}` : " Vous pouvez la corriger et la renvoyer."}</div>}{error && <div className="mb-4 rounded-xl border border-red-100 bg-red-50 p-3 text-sm text-red-700">{error}</div>}<div className="flex flex-col gap-4"><input required placeholder="Domaine d'expertise" value={form.domain} onChange={(e) => setForm({ ...form, domain: e.target.value })} className="rounded-lg border border-gray-200 px-3 py-2 text-sm" /><input required min={0} type="number" placeholder="Années d'expérience" value={form.years_experience} onChange={(e) => setForm({ ...form, years_experience: e.target.value })} className="rounded-lg border border-gray-200 px-3 py-2 text-sm" /><input placeholder="Titre professionnel" value={form.headline} onChange={(e) => setForm({ ...form, headline: e.target.value })} className="rounded-lg border border-gray-200 px-3 py-2 text-sm" /><textarea placeholder="Pourquoi souhaitez-vous devenir instructeur ? (optionnel)" value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} className="min-h-24 rounded-lg border border-gray-200 px-3 py-2 text-sm" /><button type="submit" disabled={loading} className="btn-primary">{loading ? "Envoi..." : application?.status === "rejected" ? "Renvoyer la demande" : "Envoyer ma demande"}</button></div></form></div>;
}

