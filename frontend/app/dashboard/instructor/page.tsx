"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  BookOpen,
  FileText,
  Users,
  Star,
  WalletCards,
  Video,
  PlusCircle,
  ArrowRight,
  CalendarDays,
  MessageSquareText,
  BarChart3,
} from "lucide-react";
import { api, ApiError, formatPrice } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import GuardScreen from "@/components/ui/GuardScreen";

interface Overview {
  courses: number;
  published_courses: number;
  pdfs: number;
  published_pdfs: number;
  formations: number;
  published_formations: number;
  unique_students: number;
  rating_avg: number;
  reviews_count: number;
  questions_count: number;
  upcoming_sessions: { id: number; formation_title: string; session_number: number; scheduled_at: string; duration_minutes: number; started_at: string | null }[];
  recent_students: { user_id: number; name: string; email: string; content_title: string; progress_percent: number; acquired_at: string }[];
  recent_reviews: { id: number; student: string; rating: number; comment: string; target_title: string; created_at: string }[];
}

interface FinanceSummary {
  gross_revenue: string;
  total_earnings: string;
  available_balance: string;
  paid_out: string;
  sales_count: number;
}

export default function InstructorDashboard() {
  const { ready } = useAuthGuard();
  const { user } = useAuth();
  const [overview, setOverview] = useState<Overview | null>(null);
  const [finance, setFinance] = useState<FinanceSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!ready || !user || !["instructor", "admin"].includes(user.role)) return;
    Promise.all([
      api.get<Overview>("/auth/instructor/overview/"),
      api.get<FinanceSummary>("/payments/instructor/finance/"),
    ])
      .then(([o, f]) => { setOverview(o); setFinance(f); })
      .catch((e) => setError(e instanceof ApiError ? e.message : "Impossible de charger le tableau de bord."))
      .finally(() => setLoading(false));
  }, [ready, user]);

  if (!ready) return <GuardScreen />;
  if (user && user.role !== "instructor" && user.role !== "admin") return <BecomeInstructor />;
  if (loading) return <div className="card p-10 text-center text-gray-500">Chargement de votre espace instructeur...</div>;

  return (
    <div className="min-w-0">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold">Aperçu instructeur</h1>
          <p className="mt-1 text-sm text-gray-500">Pilotez vos contenus, apprenants, séances et revenus depuis un seul espace.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link href="/dashboard/instructor/courses/new" className="btn-primary !py-2 !text-xs"><PlusCircle size={14} /> Nouveau cours</Link>
          <Link href="/dashboard/instructor/formations/new" className="btn-outline !py-2 !text-xs"><Video size={14} /> Nouvelle formation</Link>
        </div>
      </div>

      {error && <div className="mb-5 rounded-xl border border-red-100 bg-red-50 p-3 text-sm text-red-700">{error}</div>}

      <div className="mb-6 grid grid-cols-2 gap-3 xl:grid-cols-4 2xl:grid-cols-8">
        <Kpi href="/dashboard/instructor/courses" icon={<BookOpen size={19} />} label="Cours" value={overview?.courses || 0} note={`${overview?.published_courses || 0} publiés`} />
        <Kpi href="/dashboard/instructor/pdfs" icon={<FileText size={19} />} label="PDF" value={overview?.pdfs || 0} note={`${overview?.published_pdfs || 0} publiés`} />
        <Kpi href="/dashboard/instructor/formations" icon={<Video size={19} />} label="Formations" value={overview?.formations || 0} note={`${overview?.published_formations || 0} publiées`} />
        <Kpi href="/dashboard/instructor/students" icon={<Users size={19} />} label="Étudiants" value={overview?.unique_students || 0} />
        <Kpi href="/dashboard/instructor/reviews" icon={<Star size={19} />} label="Note moyenne" value={(overview?.rating_avg || 0).toFixed(1)} note={`${overview?.reviews_count || 0} avis`} />
        <Kpi href="/dashboard/instructor/reviews?view=questions" icon={<MessageSquareText size={19} />} label="Questions" value={overview?.questions_count || 0} />
        <Kpi href="/dashboard/instructor/finance" icon={<WalletCards size={19} />} label="Solde disponible" value={formatPrice(finance?.available_balance || 0)} />
        <Kpi href="/dashboard/instructor/analytics" icon={<BarChart3 size={19} />} label="Ventes" value={finance?.sales_count || 0} />
      </div>

      <div className="mb-6 grid gap-5 xl:grid-cols-2">
        <CompactCard title="Prochaines séances" subtitle="Vos rendez-vous live LearnEas" footer={<Link href="/dashboard/instructor/sessions" className="text-xs font-semibold text-brand-700">Toutes les séances <ArrowRight className="inline" size={13} /></Link>}>
          {(overview?.upcoming_sessions || []).map((s) => (
            <div key={s.id} className="flex items-center gap-3 border-b border-gray-100 py-2.5 last:border-0">
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-brand-50 text-brand-700"><CalendarDays size={16} /></span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold">{s.formation_title} · séance {s.session_number}</p>
                <p className="text-[11px] text-gray-400">{new Date(s.scheduled_at).toLocaleString("fr-FR")} · {s.duration_minutes} min</p>
              </div>
              <Link href={`/live/session/${s.id}`} className="text-xs font-semibold text-brand-700">Salle</Link>
            </div>
          ))}
          {!overview?.upcoming_sessions?.length && <Empty text="Aucune séance à venir." />}
        </CompactCard>

        <CompactCard title="Étudiants récents" subtitle="Dernières inscriptions à vos cours" footer={<Link href="/dashboard/instructor/students" className="text-xs font-semibold text-brand-700">Voir les étudiants <ArrowRight className="inline" size={13} /></Link>}>
          {(overview?.recent_students || []).map((s, idx) => (
            <div key={`${s.user_id}-${idx}`} className="flex items-center gap-3 border-b border-gray-100 py-2.5 last:border-0">
              <div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold">{s.name}</p><p className="truncate text-[11px] text-gray-400">{s.content_title}</p></div>
              <span className="text-xs font-semibold text-gray-500">{s.progress_percent}%</span>
            </div>
          ))}
          {!overview?.recent_students?.length && <Empty text="Aucune inscription pour le moment." />}
        </CompactCard>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.1fr_.9fr]">
        <div className="card p-5">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div><h2 className="font-bold">Performance financière</h2><p className="text-xs text-gray-500">Revenus générés par vos ventes payées</p></div>
            <Link href="/dashboard/instructor/finance" className="text-xs font-semibold text-brand-700">Gérer les versements</Link>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <MiniStat label="Chiffre d'affaires" value={formatPrice(finance?.gross_revenue || 0)} />
            <MiniStat label="Votre part" value={formatPrice(finance?.total_earnings || 0)} />
            <MiniStat label="Déjà versé" value={formatPrice(finance?.paid_out || 0)} />
          </div>
        </div>

        <div className="card p-5">
          <div className="mb-3 flex items-center justify-between"><div><h2 className="font-bold">Avis récents</h2><p className="text-xs text-gray-500">Retour des apprenants</p></div><Link href="/dashboard/instructor/reviews" className="text-xs font-semibold text-brand-700">Voir tout</Link></div>
          <div className="max-h-48 overflow-y-auto pr-1">
            {(overview?.recent_reviews || []).map((r) => <div key={r.id} className="border-b border-gray-100 py-2.5 last:border-0"><div className="flex justify-between gap-2"><p className="text-sm font-semibold">{r.student}</p><span className="text-xs font-bold text-amber-500">{r.rating}/5</span></div><p className="truncate text-[11px] text-gray-400">{r.target_title}</p>{r.comment && <p className="mt-1 line-clamp-2 text-xs text-gray-600">{r.comment}</p>}</div>)}
            {!overview?.recent_reviews?.length && <Empty text="Aucun avis reçu." />}
          </div>
        </div>
      </div>
    </div>
  );
}

function Kpi({ href, icon, label, value, note }: { href: string; icon: React.ReactNode; label: string; value: string | number; note?: string }) {
  return <Link href={href} className="card group p-4 transition hover:-translate-y-0.5 hover:shadow-soft"><div className="mb-3 flex items-center justify-between"><span className="grid h-9 w-9 place-items-center rounded-xl bg-brand-50 text-brand-700">{icon}</span><ArrowRight size={14} className="text-gray-300 transition group-hover:text-brand-600" /></div><p className="text-lg font-extrabold leading-tight">{value}</p><p className="mt-1 text-xs text-gray-500">{label}</p>{note && <p className="mt-1 text-[10px] text-gray-400">{note}</p>}</Link>;
}
function CompactCard({ title, subtitle, footer, children }: { title: string; subtitle: string; footer: React.ReactNode; children: React.ReactNode }) { return <div className="card flex h-[310px] flex-col p-5"><div className="mb-3"><h2 className="font-bold">{title}</h2><p className="text-xs text-gray-500">{subtitle}</p></div><div className="min-h-0 flex-1 overflow-y-auto pr-1">{children}</div><div className="mt-3 border-t border-gray-100 pt-3">{footer}</div></div>; }
function MiniStat({ label, value }: { label: string; value: string }) { return <div className="rounded-xl bg-gray-50 p-4"><p className="text-xs text-gray-500">{label}</p><p className="mt-1 text-lg font-extrabold">{value}</p></div>; }
function Empty({ text }: { text: string }) { return <div className="py-8 text-center text-xs text-gray-400">{text}</div>; }

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
    e.preventDefault(); setLoading(true); setError("");
    try { setApplication(await api.post("/auth/become-instructor/", form)); }
    catch (e) { setError(e instanceof ApiError ? e.message : "Impossible d'envoyer la demande."); }
    finally { setLoading(false); }
  }

  if (loading && !application) return <GuardScreen />;
  if (application?.status === "pending") return <div className="container-app flex min-h-[60vh] items-center justify-center py-16"><div className="card w-full max-w-lg p-8"><span className="badge bg-amber-50 text-amber-700">En attente de validation</span><h1 className="mt-4 text-2xl font-extrabold">Votre demande instructeur a été envoyée</h1><p className="mt-2 text-sm leading-6 text-gray-500">Un administrateur doit vérifier votre profil avant d'activer les fonctions de publication et de paiement.</p></div></div>;

  return <div className="container-app flex min-h-[60vh] items-center justify-center py-16"><form onSubmit={handleSubmit} className="card w-full max-w-md p-8"><h1 className="mb-1 text-2xl font-extrabold">Devenir instructeur</h1><p className="mb-6 text-sm text-gray-500">Envoyez votre demande. L'administration la valide avant l'ouverture de votre espace instructeur.</p>{application?.status === "rejected" && <div className="mb-4 rounded-xl border border-red-100 bg-red-50 p-3 text-sm text-red-700">Votre précédente demande a été refusée.{application.review_note ? ` Motif : ${application.review_note}` : " Vous pouvez la corriger et la renvoyer."}</div>}{error && <div className="mb-4 rounded-xl border border-red-100 bg-red-50 p-3 text-sm text-red-700">{error}</div>}<div className="flex flex-col gap-4"><input required placeholder="Domaine d'expertise" value={form.domain} onChange={(e) => setForm({ ...form, domain: e.target.value })} className="rounded-lg border border-gray-200 px-3 py-2 text-sm" /><input required min={0} type="number" placeholder="Années d'expérience" value={form.years_experience} onChange={(e) => setForm({ ...form, years_experience: e.target.value })} className="rounded-lg border border-gray-200 px-3 py-2 text-sm" /><input placeholder="Titre professionnel" value={form.headline} onChange={(e) => setForm({ ...form, headline: e.target.value })} className="rounded-lg border border-gray-200 px-3 py-2 text-sm" /><textarea placeholder="Pourquoi souhaitez-vous devenir instructeur ?" value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} className="min-h-24 rounded-lg border border-gray-200 px-3 py-2 text-sm" /><button type="submit" disabled={loading} className="btn-primary">{loading ? "Envoi..." : application?.status === "rejected" ? "Renvoyer la demande" : "Envoyer ma demande"}</button></div></form></div>;
}
