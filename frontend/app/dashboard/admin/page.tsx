"use client";

import { Suspense, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  ArrowRight,
  BadgeDollarSign,
  BookOpen,
  CheckCircle2,
  DollarSign,
  ExternalLink,
  FileText,
  Library,
  Loader2,
  RefreshCw,
  Search,
  Settings,
  ShoppingBag,
  Star,
  Tags,
  Users,
  UserCheck,
  Video,
  WalletCards,
  XCircle,
} from "lucide-react";
import { api, ApiError, formatPrice } from "@/lib/api";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import GuardScreen from "@/components/ui/GuardScreen";
import AdminSidebar, { AdminTab } from "@/components/admin/AdminSidebar";
import AdminModal from "@/components/admin/AdminModal";

type Paginated<T> = { count: number; next: string | null; previous: string | null; results: T[] };

type Order = {
  id: number;
  status: string;
  provider: string;
  total_amount: string;
  invoice_number: string;
  created_at: string;
  paid_at: string | null;
  customer_name: string;
  customer_email: string;
  items: { id: number; title: string; item_type: string; instructor_name: string; unit_price: string }[];
};

type Payout = {
  id: number;
  instructor: number;
  instructor_name: string;
  instructor_email: string;
  amount: string;
  status: string;
  method: string;
  account_reference_snapshot: string;
  requested_at: string;
  processed_at: string | null;
  reference: string;
  note: string;
};

type Session = {
  id: number;
  formation_id: number;
  formation_title: string;
  organizer_name: string;
  session_number: number;
  scheduled_at: string;
  duration_minutes: number;
  completed: boolean;
  started_at: string | null;
  ended_at: string | null;
  actual_duration_minutes: number;
};

type SessionReport = {
  organizers: { id: number; name: string; email: string }[];
  participants: {
    user_id: number;
    name: string;
    email: string;
    role: string;
    first_join: string | null;
    last_leave: string | null;
    total_seconds: number;
  }[];
  session: Session;
};

type Overview = {
  users: number;
  active_users: number;
  inactive_users: number;
  students: number;
  instructors: number;
  pending_instructor_applications: number;
  courses: number;
  pdfs: number;
  formations: number;
  orders: number;
  paid_orders: number;
  total_revenue: string;
  platform_fees: string;
  instructor_earnings: string;
  pending_payout_count: number;
  pending_payout_amount: string;
  platform_commission_percent: number;
  minimum_payout_amount: string;
  recent_sessions: {
    id: number;
    formation: string;
    organizer: string;
    scheduled_at: string;
    actual_duration_minutes: number;
    participants: number;
    completed: boolean;
  }[];
};

type AdminUser = {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role: "admin" | "instructor" | "student";
  is_active: boolean;
  is_staff: boolean;
  date_joined: string;
  last_login: string | null;
  country: string;
  headline: string;
  domain: string;
};

type Course = {
  id: number;
  title: string;
  slug: string;
  published: boolean;
  featured: boolean;
  price: string;
  students_count: number;
  created_at: string;
  instructor: { full_name: string };
};

type PdfProduct = {
  id: number;
  title: string;
  slug: string;
  published: boolean;
  featured: boolean;
  price: string;
  downloads_count: number;
  page_count: number;
  created_at: string;
  instructor: { full_name: string };
};

type Formation = {
  id: number;
  title: string;
  slug: string;
  published: boolean;
  status: string;
  price: string;
  students_count: number;
  start_date: string;
  created_at: string;
  instructor: { full_name: string };
};

type InstructorApplication = {
  id: number;
  user: number;
  user_name: string;
  user_email: string;
  domain: string;
  years_experience: number;
  headline: string;
  message: string;
  status: "pending" | "approved" | "rejected";
  review_note: string;
  reviewed_by_name: string;
  reviewed_at: string | null;
  created_at: string;
};

type Category = { id: number; name: string; slug: string; icon: string; description: string; courses_count: number };

type Faq = { id: number; author: number; question: string; answer: string; audience: string; order: number; created_at: string };
type Review = { id: number; user: { full_name: string }; target_title: string; target_type: string; rating: number; comment: string; created_at: string };

type PlatformSettings = {
  site_name: string;
  support_email: string;
  registration_enabled: boolean;
  instructor_applications_enabled: boolean;
  platform_commission_percent: number;
  minimum_payout_amount: string;
  updated_at: string;
};

const ADMIN_TABS: AdminTab[] = ["overview", "users", "applications", "content", "orders", "payouts", "sessions", "categories", "moderation", "settings"];

function unwrap<T>(data: Paginated<T> | T[]): T[] {
  return Array.isArray(data) ? data : data.results;
}

function toError(error: unknown): string {
  return error instanceof ApiError ? error.message : "Une erreur est survenue.";
}

export default function AdminDashboard() {
  return (
    <Suspense fallback={<GuardScreen />}>
      <AdminDashboardContent />
    </Suspense>
  );
}

function AdminDashboardContent() {
  const { ready } = useAuthGuard({ roles: ["admin"], redirectTo: "/" });
  const searchParams = useSearchParams();
  const rawTab = searchParams.get("tab") || "overview";
  const tab: AdminTab = ADMIN_TABS.includes(rawTab as AdminTab) ? (rawTab as AdminTab) : "overview";

  if (!ready) return <GuardScreen />;

  return (
    <div className="container-app py-8">
      <div className="grid gap-6 lg:grid-cols-[235px_minmax(0,1fr)]">
        <AdminSidebar activeTab={tab} />
        <main className="min-w-0">
          {tab === "overview" && <OverviewTab key={searchParams.toString()} />}
          {tab === "users" && <UsersTab key={searchParams.toString()} />}
          {tab === "applications" && <ApplicationsTab key={searchParams.toString()} />}
          {tab === "content" && <ContentTab key={searchParams.toString()} />}
          {tab === "orders" && <OrdersTab key={searchParams.toString()} />}
          {tab === "payouts" && <PayoutsTab key={searchParams.toString()} />}
          {tab === "sessions" && <SessionsTab key={searchParams.toString()} />}
          {tab === "categories" && <CategoriesTab key={searchParams.toString()} />}
          {tab === "moderation" && <ModerationTab key={searchParams.toString()} />}
          {tab === "settings" && <SettingsTab key={searchParams.toString()} />}
        </main>
      </div>
    </div>
  );
}

function PageHeader({ title, description, actions }: { title: string; description: string; actions?: React.ReactNode }) {
  return (
    <div className="mb-6 flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 className="text-xl font-bold">{title}</h1>
        <p className="mt-1 text-sm text-gray-500">{description}</p>
      </div>
      {actions}
    </div>
  );
}

function OverviewTab() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [payouts, setPayouts] = useState<Payout[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [reportId, setReportId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const [stats, payoutData] = await Promise.all([
        api.get<Overview>("/payments/admin/overview/"),
        api.get<Paginated<Payout> | Payout[]>("/payments/payouts/?status=pending&ordering=-requested_at"),
      ]);
      setOverview(stats);
      setPayouts(unwrap(payoutData));
    } catch (e) {
      setError(toError(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function markPaid(id: number) {
    const reference = window.prompt("Référence du paiement (optionnel)") || "";
    try {
      await api.post(`/payments/payouts/${id}/mark_paid/`, { reference });
      setMessage("Versement marqué comme payé.");
      await load();
    } catch (e) {
      setMessage(toError(e));
    }
  }

  return (
    <>
      <PageHeader
        title="Pilotage de la plateforme"
        description="Vue synthétique de l'activité, des revenus, des versements et des séances."
        actions={
          <a
            href={(process.env.NEXT_PUBLIC_API_URL || "/api").replace(/\/api\/?$/, "/admin/")}
            target="_blank"
            rel="noreferrer"
            className="btn-outline !py-2 !text-xs"
          >
            Administration Django <ExternalLink size={14} />
          </a>
        }
      />

      {error && <Alert text={error} tone="error" />}
      {loading && !overview ? <LoadingBlock /> : (
        <>
          <div className="mb-6 grid grid-cols-2 gap-3 xl:grid-cols-4 2xl:grid-cols-8">
            <Kpi href="/dashboard/admin?tab=orders&status=paid" icon={<DollarSign size={19} />} label="Chiffre d'affaires" value={formatPrice(overview?.total_revenue || 0)} />
            <Kpi href="/dashboard/admin?tab=orders&status=paid" icon={<BadgeDollarSign size={19} />} label="Commission plateforme" value={formatPrice(overview?.platform_fees || 0)} />
            <Kpi href="/dashboard/admin?tab=payouts" icon={<WalletCards size={19} />} label="Gains instructeurs" value={formatPrice(overview?.instructor_earnings || 0)} />
            <Kpi href="/dashboard/admin?tab=users" icon={<Users size={19} />} label="Utilisateurs" value={overview?.users || 0} />
            <Kpi href="/dashboard/admin?tab=users&role=instructor" icon={<Users size={19} />} label="Instructeurs" value={overview?.instructors || 0} />
            <Kpi href="/dashboard/admin?tab=content&type=course" icon={<BookOpen size={19} />} label="Cours" value={overview?.courses || 0} />
            <Kpi href="/dashboard/admin?tab=content&type=pdf" icon={<FileText size={19} />} label="PDF" value={overview?.pdfs || 0} />
            <Kpi href="/dashboard/admin?tab=content&type=formation" icon={<Video size={19} />} label="Formations live" value={overview?.formations || 0} />
          </div>

          <div className="mb-6 grid grid-cols-1 gap-5 xl:grid-cols-2">
            <CompactCard
              title="Versements instructeurs"
              subtitle={`En attente : ${overview?.pending_payout_count || 0} · ${formatPrice(overview?.pending_payout_amount || 0)}`}
              footer={<Link href="/dashboard/admin?tab=payouts" className="text-xs font-semibold text-brand-700">Voir tous les versements <ArrowRight className="inline" size={13} /></Link>}
            >
              {payouts.filter((p) => p.status === "pending").slice(0, 8).map((p) => (
                <div key={p.id} className="flex items-center gap-3 border-b border-gray-100 py-2.5 last:border-0">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-semibold">{p.instructor_name}</p>
                    <p className="truncate text-[11px] text-gray-400">{p.method} · {p.instructor_email}</p>
                  </div>
                  <strong className="whitespace-nowrap text-sm">{formatPrice(p.amount)}</strong>
                  <button onClick={() => markPaid(p.id)} className="rounded-lg border border-gray-200 px-2 py-1 text-[11px] font-semibold hover:bg-gray-50">Payer</button>
                </div>
              ))}
              {!payouts.some((p) => p.status === "pending") && <Empty text="Aucun versement en attente." />}
            </CompactCard>

            <CompactCard
              title="Contrôle des séances"
              subtitle="Présences, organisateur et durée réelle"
              footer={<Link href="/dashboard/admin?tab=sessions" className="text-xs font-semibold text-brand-700">Voir toutes les séances <ArrowRight className="inline" size={13} /></Link>}
            >
              {(overview?.recent_sessions || []).map((s) => (
                <div key={s.id} className="border-b border-gray-100 py-2.5 last:border-0">
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold">{s.formation}</p>
                      <p className="truncate text-[11px] text-gray-400">{s.organizer} · {new Date(s.scheduled_at).toLocaleString("fr-FR")}</p>
                    </div>
                    <span className={`badge shrink-0 ${s.completed ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-600"}`}>{s.completed ? "Terminée" : "Planifiée"}</span>
                  </div>
                  <div className="mt-1.5 flex items-center justify-between gap-2">
                    <p className="text-[11px] text-gray-500">{s.actual_duration_minutes || 0} min · {s.participants} participant(s)</p>
                    <button onClick={() => setReportId(s.id)} className="text-[11px] font-semibold text-brand-700 hover:underline">Voir participants et durées</button>
                  </div>
                </div>
              ))}
              {(overview?.recent_sessions || []).length === 0 && <Empty text="Aucune séance planifiée." />}
            </CompactCard>
          </div>

          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <InfoCard label="Utilisateurs actifs" value={`${overview?.active_users || 0}`} note={`${overview?.inactive_users || 0} compte(s) désactivé(s)`} href="/dashboard/admin?tab=users&active=true" />
            <InfoCard label="Demandes instructeur" value={`${overview?.pending_instructor_applications || 0}`} note="En attente de validation" href="/dashboard/admin?tab=applications&status=pending" />
            <InfoCard label="Commandes payées" value={`${overview?.paid_orders || 0}`} note={`${overview?.orders || 0} commande(s) au total`} href="/dashboard/admin?tab=orders&status=paid" />
            <InfoCard label="Politique de versement" value={`${overview?.platform_commission_percent || 0}%`} note={`Retrait minimum : ${formatPrice(overview?.minimum_payout_amount || 0)}`} href="/dashboard/admin?tab=settings" />
          </div>
        </>
      )}
      {message && <div className="mt-4"><Alert text={message} /></div>}
      <SessionReportModal sessionId={reportId} onClose={() => setReportId(null)} />
    </>
  );
}

function UsersTab() {
  const params = useSearchParams();
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [count, setCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [role, setRole] = useState(params.get("role") || "");
  const [active, setActive] = useState(params.get("active") || "");
  const [page, setPage] = useState(1);
  const [createOpen, setCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState({ email: "", first_name: "", last_name: "", role: "student", password: "" });
  const [creating, setCreating] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    const query = new URLSearchParams({ page: String(page), ordering: "-date_joined" });
    if (search) query.set("search", search);
    if (role) query.set("role", role);
    if (active) query.set("is_active", active === "true" ? "true" : "false");
    try {
      const data = await api.get<Paginated<AdminUser>>(`/auth/admin/users/?${query}`);
      setUsers(data.results); setCount(data.count);
    } catch (e) { setError(toError(e)); }
    finally { setLoading(false); }
  }, [search, role, active, page]);

  useEffect(() => { const t = setTimeout(load, 200); return () => clearTimeout(t); }, [load]);

  async function updateUser(id: number, patch: Partial<AdminUser>) {
    try {
      const updated = await api.patch<AdminUser>(`/auth/admin/users/${id}/`, patch);
      setUsers((current) => current.map((u) => u.id === id ? updated : u));
    } catch (e) { setError(toError(e)); }
  }

  async function createUser(event: React.FormEvent) {
    event.preventDefault();
    setCreating(true); setError("");
    try {
      await api.post("/auth/admin/users/", createForm);
      setCreateOpen(false);
      setCreateForm({ email: "", first_name: "", last_name: "", role: "student", password: "" });
      setPage(1);
      await load();
    } catch (e) { setError(toError(e)); }
    finally { setCreating(false); }
  }

  return (
    <>
      <PageHeader title="Utilisateurs" description="Recherchez les comptes, gérez les rôles et activez ou désactivez l'accès à la plateforme." actions={<button onClick={() => setCreateOpen(true)} className="btn-primary !py-2 !text-xs">Nouvel utilisateur</button>} />
      <div className="card mb-4 flex flex-wrap gap-3 p-4">
        <SearchInput value={search} onChange={(v) => { setSearch(v); setPage(1); }} placeholder="Nom, email..." />
        <select value={role} onChange={(e) => { setRole(e.target.value); setPage(1); }} className="input-admin">
          <option value="">Tous les rôles</option><option value="student">Étudiants</option><option value="instructor">Instructeurs</option><option value="admin">Administrateurs</option>
        </select>
        <select value={active} onChange={(e) => { setActive(e.target.value); setPage(1); }} className="input-admin">
          <option value="">Tous les états</option><option value="true">Actifs</option><option value="false">Désactivés</option>
        </select>
      </div>
      {error && <Alert text={error} tone="error" />}
      <div className="card overflow-x-auto">
        <table className="w-full min-w-[840px] text-sm">
          <thead className="table-head"><tr><th>Utilisateur</th><th>Rôle</th><th>État</th><th>Inscription</th><th>Dernière connexion</th></tr></thead>
          <tbody className="divide-y divide-gray-100">
            {users.map((u) => (
              <tr key={u.id}>
                <td className="px-4 py-3"><p className="font-semibold">{u.full_name}</p><p className="text-xs text-gray-400">{u.email}</p></td>
                <td className="px-4 py-3">
                  <select value={u.role} onChange={(e) => updateUser(u.id, { role: e.target.value as AdminUser["role"] })} className="rounded-lg border border-gray-200 px-2 py-1.5 text-xs">
                    <option value="student">Étudiant</option><option value="instructor">Instructeur</option><option value="admin">Admin</option>
                  </select>
                </td>
                <td className="px-4 py-3"><Toggle checked={u.is_active} onChange={(value) => updateUser(u.id, { is_active: value })} label={u.is_active ? "Actif" : "Désactivé"} /></td>
                <td className="px-4 py-3 text-gray-500">{new Date(u.date_joined).toLocaleDateString("fr-FR")}</td>
                <td className="px-4 py-3 text-gray-500">{u.last_login ? new Date(u.last_login).toLocaleString("fr-FR") : "Jamais"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {loading && <LoadingBlock compact />}
        {!loading && users.length === 0 && <Empty text="Aucun utilisateur ne correspond aux filtres." />}
      </div>
      <Pagination page={page} count={count} onPage={setPage} />
      <AdminModal open={createOpen} title="Créer un utilisateur" onClose={() => setCreateOpen(false)}>
        <form onSubmit={createUser} className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2"><label className="label-admin">Prénom<input className="input-admin w-full" value={createForm.first_name} onChange={(e) => setCreateForm({ ...createForm, first_name: e.target.value })} /></label><label className="label-admin">Nom<input className="input-admin w-full" value={createForm.last_name} onChange={(e) => setCreateForm({ ...createForm, last_name: e.target.value })} /></label></div>
          <label className="label-admin">Email<input required type="email" className="input-admin w-full" value={createForm.email} onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })} /></label>
          <label className="label-admin">Rôle<select className="input-admin w-full" value={createForm.role} onChange={(e) => setCreateForm({ ...createForm, role: e.target.value })}><option value="student">Étudiant</option><option value="instructor">Instructeur</option><option value="admin">Administrateur</option></select></label>
          <label className="label-admin">Mot de passe temporaire<input required minLength={8} type="password" className="input-admin w-full" value={createForm.password} onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })} /></label>
          <p className="text-xs text-gray-400">Le nom d'utilisateur technique est généré automatiquement à partir de l'email ; l'utilisateur se connecte avec son email.</p>
          <div className="flex justify-end gap-2"><button type="button" onClick={() => setCreateOpen(false)} className="btn-outline">Annuler</button><button disabled={creating} type="submit" className="btn-primary">{creating ? "Création..." : "Créer le compte"}</button></div>
        </form>
      </AdminModal>
    </>
  );
}

function ApplicationsTab() {
  const params = useSearchParams();
  const [applications, setApplications] = useState<InstructorApplication[]>([]);
  const [count, setCount] = useState(0);
  const [statusFilter, setStatusFilter] = useState(params.get("status") || "");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<InstructorApplication | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    const q = new URLSearchParams({ page: String(page), ordering: "-created_at" });
    if (statusFilter) q.set("status", statusFilter);
    if (search) q.set("search", search);
    try {
      const data = await api.get<Paginated<InstructorApplication>>(`/auth/admin/instructor-applications/?${q}`);
      setApplications(data.results); setCount(data.count);
    } catch (e) { setError(toError(e)); }
    finally { setLoading(false); }
  }, [statusFilter, search, page]);

  useEffect(() => { const t = setTimeout(load, 200); return () => clearTimeout(t); }, [load]);

  async function review(application: InstructorApplication, action: "approve" | "reject") {
    const review_note = window.prompt(action === "approve" ? "Note de validation (optionnel)" : "Motif du refus (recommandé)") || "";
    if (action === "reject" && !review_note && !window.confirm("Refuser sans indiquer de motif ?")) return;
    try {
      const updated = await api.post<InstructorApplication>(`/auth/admin/instructor-applications/${application.id}/${action}/`, { review_note });
      setApplications((current) => current.map((a) => a.id === updated.id ? updated : a));
      if (selected?.id === updated.id) setSelected(updated);
    } catch (e) { setError(toError(e)); }
  }

  return (
    <>
      <PageHeader title="Demandes instructeur" description="Validez les profils avant de leur donner les droits de publication et l'accès aux revenus instructeur." />
      <div className="card mb-4 flex flex-wrap gap-3 p-4">
        <SearchInput value={search} onChange={(v) => { setSearch(v); setPage(1); }} placeholder="Nom, email, domaine..." />
        <select className="input-admin" value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}><option value="">Tous les statuts</option><option value="pending">En attente</option><option value="approved">Approuvées</option><option value="rejected">Refusées</option></select>
      </div>
      {error && <Alert text={error} tone="error" />}
      <div className="card overflow-x-auto"><table className="w-full min-w-[920px] text-sm"><thead className="table-head"><tr><th>Candidat</th><th>Domaine</th><th>Expérience</th><th>Demande</th><th>Statut</th><th>Actions</th></tr></thead><tbody className="divide-y divide-gray-100">{applications.map((a) => <tr key={a.id}><td className="px-4 py-3"><p className="font-semibold">{a.user_name}</p><p className="text-xs text-gray-400">{a.user_email}</p></td><td className="px-4 py-3"><p className="font-medium">{a.domain}</p><p className="text-xs text-gray-400">{a.headline || "—"}</p></td><td className="px-4 py-3">{a.years_experience} an(s)</td><td className="px-4 py-3 text-gray-500">{new Date(a.created_at).toLocaleDateString("fr-FR")}</td><td className="px-4 py-3"><StatusBadge status={a.status} /></td><td className="px-4 py-3"><div className="flex gap-2"><button onClick={() => setSelected(a)} className="text-xs font-semibold text-brand-700">Détails</button>{a.status === "pending" && <><button onClick={() => review(a, "approve")} className="text-xs font-semibold text-emerald-700">Approuver</button><button onClick={() => review(a, "reject")} className="text-xs font-semibold text-red-600">Refuser</button></>}</div></td></tr>)}</tbody></table>{loading && <LoadingBlock compact />}{!loading && applications.length === 0 && <Empty text="Aucune demande instructeur trouvée." />}</div>
      <Pagination page={page} count={count} onPage={setPage} />
      <AdminModal open={!!selected} title={selected ? `Demande de ${selected.user_name}` : "Demande instructeur"} onClose={() => setSelected(null)}>
        {selected && <div className="space-y-4"><div className="grid gap-3 sm:grid-cols-2"><MiniMetric label="Email" value={selected.user_email} /><MiniMetric label="Domaine" value={selected.domain} /><MiniMetric label="Expérience" value={`${selected.years_experience} an(s)`} /><MiniMetric label="Statut" value={selected.status} /></div><div className="rounded-xl bg-gray-50 p-4"><p className="text-xs font-semibold text-gray-500">Titre professionnel</p><p className="mt-1 text-sm">{selected.headline || "—"}</p><p className="mt-4 text-xs font-semibold text-gray-500">Message</p><p className="mt-1 whitespace-pre-wrap text-sm leading-6">{selected.message || "Aucun message."}</p></div>{selected.review_note && <div className="rounded-xl border border-gray-100 p-4 text-sm"><b>Note de l'administration :</b> {selected.review_note}</div>}{selected.status === "pending" && <div className="flex justify-end gap-2"><button onClick={() => review(selected, "reject")} className="btn-outline !text-red-600">Refuser</button><button onClick={() => review(selected, "approve")} className="btn-primary"><UserCheck size={15} /> Approuver</button></div>}</div>}
      </AdminModal>
    </>
  );
}

function ContentTab() {
  const params = useSearchParams();
  const initial = params.get("type");
  const [type, setType] = useState<"course" | "pdf" | "formation">(initial === "pdf" || initial === "formation" ? initial : "course");
  const [items, setItems] = useState<(Course | PdfProduct | Formation)[]>([]);
  const [count, setCount] = useState(0);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [page, setPage] = useState(1);

  const endpoint = type === "course" ? "/catalog/courses/" : type === "pdf" ? "/catalog/pdfs/" : "/formations/";
  const newHref = type === "course" ? "/dashboard/instructor/courses/new" : type === "pdf" ? "/dashboard/instructor/pdfs/new" : "/dashboard/instructor/formations/new";

  const load = useCallback(async () => {
    setLoading(true); setError("");
    const q = new URLSearchParams({ page: String(page), ordering: "-created_at" });
    if (search) q.set("search", search);
    try {
      const data = await api.get<Paginated<Course | PdfProduct | Formation>>(`${endpoint}?${q}`);
      setItems(data.results); setCount(data.count);
    } catch (e) { setError(toError(e)); }
    finally { setLoading(false); }
  }, [endpoint, search, page]);

  useEffect(() => { const t = setTimeout(load, 200); return () => clearTimeout(t); }, [load]);

  async function patchItem(item: Course | PdfProduct | Formation, patch: Record<string, unknown>) {
    try {
      const result = await api.patch<Course | PdfProduct | Formation>(`${endpoint}${item.slug}/`, patch);
      setItems((current) => current.map((x) => x.id === item.id ? { ...x, ...result } : x));
    } catch (e) { setError(toError(e)); }
  }

  async function deleteItem(item: Course | PdfProduct | Formation) {
    if (!window.confirm(`Supprimer définitivement « ${item.title} » ?`)) return;
    try {
      await api.del(`${endpoint}${item.slug}/`);
      await load();
    } catch (e) { setError(toError(e)); }
  }

  return (
    <>
      <PageHeader title="Contenus" description="Supervisez la publication des cours, PDF et formations interactives." actions={<Link href={newHref} className="btn-primary !py-2 !text-xs">Créer un contenu</Link>} />
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="flex rounded-xl border border-gray-200 bg-white p-1">
          {(["course", "pdf", "formation"] as const).map((value) => (
            <button key={value} onClick={() => { setType(value); setPage(1); }} className={`rounded-lg px-3 py-2 text-xs font-semibold ${type === value ? "bg-brand-50 text-brand-700" : "text-gray-500"}`}>
              {value === "course" ? "Cours" : value === "pdf" ? "PDF" : "Formations"}
            </button>
          ))}
        </div>
        <SearchInput value={search} onChange={(v) => { setSearch(v); setPage(1); }} placeholder="Rechercher un contenu..." />
      </div>
      {error && <Alert text={error} tone="error" />}
      <div className="card overflow-x-auto">
        <table className="w-full min-w-[800px] text-sm">
          <thead className="table-head"><tr><th>Contenu</th><th>Instructeur</th><th>Prix</th><th>Indicateur</th><th>Publié</th>{type !== "formation" && <th>Mis en avant</th>}<th>Actions</th></tr></thead>
          <tbody className="divide-y divide-gray-100">
            {items.map((item) => {
              const isCourse = type === "course";
              const isPdf = type === "pdf";
              const indicator = isCourse ? `${(item as Course).students_count} étudiant(s)` : isPdf ? `${(item as PdfProduct).page_count} pages · ${(item as PdfProduct).downloads_count} achat(s)` : `${(item as Formation).students_count} inscrit(s) · ${(item as Formation).status}`;
              const publicHref = isCourse ? `/courses/${item.slug}` : isPdf ? `/pdfs/${item.slug}` : `/formations/${item.slug}`;
              return (
                <tr key={`${type}-${item.id}`}>
                  <td className="px-4 py-3"><p className="font-semibold">{item.title}</p><p className="text-xs text-gray-400">Créé le {new Date(item.created_at).toLocaleDateString("fr-FR")}</p></td>
                  <td className="px-4 py-3 text-gray-600">{item.instructor?.full_name || "—"}</td>
                  <td className="px-4 py-3 font-semibold">{formatPrice(item.price)}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{indicator}</td>
                  <td className="px-4 py-3"><Toggle checked={item.published} onChange={(v) => patchItem(item, { published: v })} label={item.published ? "Oui" : "Non"} /></td>
                  {type !== "formation" && <td className="px-4 py-3"><Toggle checked={(item as Course | PdfProduct).featured} onChange={(v) => patchItem(item, { featured: v })} label={(item as Course | PdfProduct).featured ? "Oui" : "Non"} /></td>}
                  <td className="px-4 py-3"><div className="flex items-center gap-3"><Link href={publicHref} className="text-xs font-semibold text-brand-700">Ouvrir</Link><button onClick={() => deleteItem(item)} className="text-xs font-semibold text-red-600">Supprimer</button></div></td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {loading && <LoadingBlock compact />}
        {!loading && items.length === 0 && <Empty text="Aucun contenu trouvé." />}
      </div>
      <Pagination page={page} count={count} onPage={setPage} />
    </>
  );
}

function OrdersTab() {
  const params = useSearchParams();
  const [orders, setOrders] = useState<Order[]>([]);
  const [count, setCount] = useState(0);
  const [statusFilter, setStatusFilter] = useState(params.get("status") || "");
  const [provider, setProvider] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState<Order | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    const q = new URLSearchParams({ page: String(page), ordering: "-created_at" });
    if (statusFilter) q.set("status", statusFilter);
    if (provider) q.set("provider", provider);
    if (search) q.set("search", search);
    try {
      const data = await api.get<Paginated<Order>>(`/payments/orders/?${q}`);
      setOrders(data.results); setCount(data.count);
    } catch (e) { setError(toError(e)); }
    finally { setLoading(false); }
  }, [statusFilter, provider, search, page]);

  useEffect(() => { const t = setTimeout(load, 200); return () => clearTimeout(t); }, [load]);

  async function setOrderStatus(order: Order, status: string) {
    if (!window.confirm(`Passer la commande ${order.invoice_number} au statut « ${status} » ?`)) return;
    try {
      const updated = await api.post<Order>(`/payments/orders/${order.id}/set_status/`, { status });
      setOrders((current) => current.map((o) => o.id === order.id ? updated : o));
      if (selected?.id === order.id) setSelected(updated);
    } catch (e) { setError(toError(e)); }
  }

  return (
    <>
      <PageHeader title="Commandes" description="Consultez les transactions et réconciliez leur statut avec les droits d'accès." />
      <div className="card mb-4 flex flex-wrap gap-3 p-4">
        <SearchInput value={search} onChange={(v) => { setSearch(v); setPage(1); }} placeholder="Facture, client..." />
        <select value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }} className="input-admin"><option value="">Tous les statuts</option><option value="pending">En attente</option><option value="paid">Payée</option><option value="failed">Échouée</option><option value="refunded">Remboursée</option></select>
        <select value={provider} onChange={(e) => { setProvider(e.target.value); setPage(1); }} className="input-admin"><option value="">Tous les moyens</option><option value="stripe">Carte</option><option value="paypal">PayPal</option><option value="mobile_money">Mobile Money</option></select>
      </div>
      {error && <Alert text={error} tone="error" />}
      <div className="card overflow-x-auto">
        <table className="w-full min-w-[900px] text-sm"><thead className="table-head"><tr><th>Facture</th><th>Client</th><th>Montant</th><th>Moyen</th><th>Statut</th><th>Date</th><th></th></tr></thead>
          <tbody className="divide-y divide-gray-100">{orders.map((o) => <tr key={o.id}><td className="px-4 py-3 font-mono text-xs">{o.invoice_number}</td><td className="px-4 py-3"><p className="font-medium">{o.customer_name}</p><p className="text-xs text-gray-400">{o.customer_email}</p></td><td className="px-4 py-3 font-semibold">{formatPrice(o.total_amount)}</td><td className="px-4 py-3 text-gray-500">{o.provider}</td><td className="px-4 py-3"><StatusBadge status={o.status} /></td><td className="px-4 py-3 text-gray-500">{new Date(o.created_at).toLocaleDateString("fr-FR")}</td><td className="px-4 py-3"><button onClick={() => setSelected(o)} className="text-xs font-semibold text-brand-700">Détails</button></td></tr>)}</tbody>
        </table>
        {loading && <LoadingBlock compact />}{!loading && orders.length === 0 && <Empty text="Aucune commande trouvée." />}
      </div>
      <Pagination page={page} count={count} onPage={setPage} />
      <AdminModal open={!!selected} title={selected ? `Commande ${selected.invoice_number}` : "Commande"} onClose={() => setSelected(null)}>
        {selected && <OrderDetails order={selected} onStatus={(status) => setOrderStatus(selected, status)} />}
      </AdminModal>
    </>
  );
}

function PayoutsTab() {
  const [payouts, setPayouts] = useState<Payout[]>([]);
  const [count, setCount] = useState(0);
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true); setError("");
    const q = new URLSearchParams({ page: String(page), ordering: "-requested_at" });
    if (statusFilter) q.set("status", statusFilter);
    if (search) q.set("search", search);
    try { const data = await api.get<Paginated<Payout>>(`/payments/payouts/?${q}`); setPayouts(data.results); setCount(data.count); }
    catch (e) { setError(toError(e)); } finally { setLoading(false); }
  }, [statusFilter, search, page]);
  useEffect(() => { const t = setTimeout(load, 200); return () => clearTimeout(t); }, [load]);

  async function process(id: number, action: "mark_paid" | "mark_failed") {
    const reference = action === "mark_paid" ? (window.prompt("Référence du versement") || "") : "";
    const note = action === "mark_failed" ? (window.prompt("Motif de l'échec") || "") : "";
    try { await api.post(`/payments/payouts/${id}/${action}/`, { reference, note }); await load(); }
    catch (e) { setError(toError(e)); }
  }

  return (
    <>
      <PageHeader title="Versements instructeurs" description="Traitez les demandes de retrait et conservez une référence de paiement." />
      <div className="card mb-4 flex flex-wrap gap-3 p-4"><SearchInput value={search} onChange={(v) => { setSearch(v); setPage(1); }} placeholder="Instructeur, référence..." /><select className="input-admin" value={statusFilter} onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}><option value="">Tous les statuts</option><option value="pending">Demandés</option><option value="paid">Payés</option><option value="failed">Échoués</option><option value="cancelled">Annulés</option></select></div>
      {error && <Alert text={error} tone="error" />}
      <div className="card overflow-x-auto"><table className="w-full min-w-[980px] text-sm"><thead className="table-head"><tr><th>Instructeur</th><th>Destination</th><th>Montant</th><th>Statut</th><th>Demandé le</th><th>Référence</th><th>Actions</th></tr></thead><tbody className="divide-y divide-gray-100">{payouts.map((p) => <tr key={p.id}><td className="px-4 py-3"><p className="font-semibold">{p.instructor_name}</p><p className="text-xs text-gray-400">{p.instructor_email}</p></td><td className="max-w-[240px] break-all px-4 py-3 text-xs text-gray-500"><b>{p.method}</b><br />{p.account_reference_snapshot || "Non renseignée"}</td><td className="px-4 py-3 font-semibold">{formatPrice(p.amount)}</td><td className="px-4 py-3"><StatusBadge status={p.status} /></td><td className="px-4 py-3 text-gray-500">{new Date(p.requested_at).toLocaleString("fr-FR")}</td><td className="px-4 py-3 text-xs text-gray-500">{p.reference || "—"}</td><td className="px-4 py-3">{p.status === "pending" ? <div className="flex gap-2"><button onClick={() => process(p.id, "mark_paid")} className="rounded-lg bg-brand-50 px-2 py-1.5 text-xs font-semibold text-brand-700">Payer</button><button onClick={() => process(p.id, "mark_failed")} className="rounded-lg bg-red-50 px-2 py-1.5 text-xs font-semibold text-red-600">Échec</button></div> : "—"}</td></tr>)}</tbody></table>{loading && <LoadingBlock compact />}{!loading && payouts.length === 0 && <Empty text="Aucun versement trouvé." />}</div>
      <Pagination page={page} count={count} onPage={setPage} />
    </>
  );
}

function SessionsTab() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [count, setCount] = useState(0);
  const [completed, setCompleted] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reportId, setReportId] = useState<number | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError("");
    const q = new URLSearchParams({ page: String(page), ordering: "-scheduled_at" });
    if (completed) q.set("completed", completed);
    if (search) q.set("search", search);
    try { const data = await api.get<Paginated<Session>>(`/sessions/?${q}`); setSessions(data.results); setCount(data.count); }
    catch (e) { setError(toError(e)); } finally { setLoading(false); }
  }, [completed, search, page]);
  useEffect(() => { const t = setTimeout(load, 200); return () => clearTimeout(t); }, [load]);

  return (
    <>
      <PageHeader title="Séances interactives" description="Contrôlez le planning, les durées réelles et les présences enregistrées sur la plateforme." />
      <div className="card mb-4 flex flex-wrap gap-3 p-4"><SearchInput value={search} onChange={(v) => { setSearch(v); setPage(1); }} placeholder="Formation, organisateur..." /><select className="input-admin" value={completed} onChange={(e) => { setCompleted(e.target.value); setPage(1); }}><option value="">Toutes les séances</option><option value="false">Planifiées / en cours</option><option value="true">Terminées</option></select></div>
      {error && <Alert text={error} tone="error" />}
      <div className="card overflow-x-auto"><table className="w-full min-w-[900px] text-sm"><thead className="table-head"><tr><th>Formation</th><th>Organisateur</th><th>Planifiée</th><th>Prévue</th><th>Réelle</th><th>État</th><th></th></tr></thead><tbody className="divide-y divide-gray-100">{sessions.map((s) => <tr key={s.id}><td className="px-4 py-3"><p className="font-semibold">{s.formation_title}</p><p className="text-xs text-gray-400">Séance {s.session_number}</p></td><td className="px-4 py-3 text-gray-600">{s.organizer_name}</td><td className="px-4 py-3 text-gray-500">{new Date(s.scheduled_at).toLocaleString("fr-FR")}</td><td className="px-4 py-3">{s.duration_minutes} min</td><td className="px-4 py-3 font-semibold">{s.actual_duration_minutes || 0} min</td><td className="px-4 py-3"><span className={`badge ${s.completed ? "bg-emerald-50 text-emerald-700" : s.started_at ? "bg-amber-50 text-amber-700" : "bg-gray-100 text-gray-600"}`}>{s.completed ? "Terminée" : s.started_at ? "En cours" : "Planifiée"}</span></td><td className="px-4 py-3"><button onClick={() => setReportId(s.id)} className="text-xs font-semibold text-brand-700">Participants & durées</button></td></tr>)}</tbody></table>{loading && <LoadingBlock compact />}{!loading && sessions.length === 0 && <Empty text="Aucune séance trouvée." />}</div>
      <Pagination page={page} count={count} onPage={setPage} />
      <SessionReportModal sessionId={reportId} onClose={() => setReportId(null)} />
    </>
  );
}

function CategoriesTab() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ name: "", description: "", icon: "BookOpen" });
  const [editing, setEditing] = useState<Category | null>(null);

  const load = useCallback(async () => {
    try { setCategories(await api.get<Category[]>("/catalog/categories/")); }
    catch (e) { setError(toError(e)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  async function save(event: React.FormEvent) {
    event.preventDefault(); setError("");
    try {
      if (editing) await api.patch(`/catalog/categories/${editing.slug}/`, form);
      else await api.post("/catalog/categories/", form);
      setForm({ name: "", description: "", icon: "BookOpen" }); setEditing(null); await load();
    } catch (e) { setError(toError(e)); }
  }

  async function remove(category: Category) {
    if (!window.confirm(`Supprimer la catégorie « ${category.name} » ?`)) return;
    try { await api.del(`/catalog/categories/${category.slug}/`); await load(); }
    catch (e) { setError(toError(e)); }
  }

  return (
    <>
      <PageHeader title="Catégories" description="Structurez le catalogue et les filtres proposés aux apprenants." />
      {error && <Alert text={error} tone="error" />}
      <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
        <div className="card overflow-x-auto"><table className="w-full min-w-[600px] text-sm"><thead className="table-head"><tr><th>Nom</th><th>Description</th><th>Cours publiés</th><th>Actions</th></tr></thead><tbody className="divide-y divide-gray-100">{categories.map((c) => <tr key={c.id}><td className="px-4 py-3 font-semibold">{c.name}</td><td className="px-4 py-3 text-gray-500">{c.description || "—"}</td><td className="px-4 py-3">{c.courses_count}</td><td className="px-4 py-3"><div className="flex gap-2"><button onClick={() => { setEditing(c); setForm({ name: c.name, description: c.description, icon: c.icon }); }} className="text-xs font-semibold text-brand-700">Modifier</button><button onClick={() => remove(c)} className="text-xs font-semibold text-red-600">Supprimer</button></div></td></tr>)}</tbody></table></div>
        <form onSubmit={save} className="card self-start p-5"><h2 className="font-bold">{editing ? "Modifier la catégorie" : "Nouvelle catégorie"}</h2><div className="mt-4 space-y-3"><label className="label-admin">Nom<input required className="input-admin w-full" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label><label className="label-admin">Description<textarea className="input-admin min-h-24 w-full" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label><label className="label-admin">Icône Lucide<input className="input-admin w-full" value={form.icon} onChange={(e) => setForm({ ...form, icon: e.target.value })} /></label><div className="flex gap-2"><button className="btn-primary flex-1" type="submit">{editing ? "Enregistrer" : "Ajouter"}</button>{editing && <button type="button" onClick={() => { setEditing(null); setForm({ name: "", description: "", icon: "BookOpen" }); }} className="btn-outline">Annuler</button>}</div></div></form>
      </div>
    </>
  );
}

function ModerationTab() {
  const [mode, setMode] = useState<"faq" | "reviews">("faq");
  const [faqs, setFaqs] = useState<Faq[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [count, setCount] = useState(0);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState<Faq | null>(null);
  const [faqForm, setFaqForm] = useState({ question: "", answer: "", audience: "all", order: 0 });

  const load = useCallback(async () => {
    setLoading(true); setError("");
    const q = new URLSearchParams({ page: String(page) });
    if (search) q.set("search", search);
    try {
      if (mode === "faq") {
        q.set("ordering", "order");
        const data = await api.get<Paginated<Faq>>(`/faq/?${q}`);
        setFaqs(data.results); setCount(data.count);
      } else {
        q.set("ordering", "-created_at");
        const data = await api.get<Paginated<Review>>(`/reviews/reviews/?${q}`);
        setReviews(data.results); setCount(data.count);
      }
    } catch (e) { setError(toError(e)); }
    finally { setLoading(false); }
  }, [mode, search, page]);

  useEffect(() => { const t = setTimeout(load, 200); return () => clearTimeout(t); }, [load]);

  async function saveFaq(event: React.FormEvent) {
    event.preventDefault(); setError("");
    try {
      if (editing) await api.patch(`/faq/${editing.id}/`, faqForm);
      else await api.post("/faq/", faqForm);
      setEditing(null); setFaqForm({ question: "", answer: "", audience: "all", order: 0 }); await load();
    } catch (e) { setError(toError(e)); }
  }

  async function deleteFaq(id: number) {
    if (!window.confirm("Supprimer cette FAQ ?")) return;
    try { await api.del(`/faq/${id}/`); await load(); } catch (e) { setError(toError(e)); }
  }

  async function deleteReview(id: number) {
    if (!window.confirm("Supprimer cet avis ? La note moyenne du contenu sera recalculée.")) return;
    try { await api.del(`/reviews/reviews/${id}/`); await load(); } catch (e) { setError(toError(e)); }
  }

  return (
    <>
      <PageHeader title="FAQ & modération" description="Administrez l'aide publique et modérez les avis publiés sur les contenus." />
      <div className="mb-4 flex rounded-xl border border-gray-200 bg-white p-1 sm:w-fit">
        <button onClick={() => { setMode("faq"); setPage(1); }} className={`rounded-lg px-4 py-2 text-xs font-semibold ${mode === "faq" ? "bg-brand-50 text-brand-700" : "text-gray-500"}`}>FAQ</button>
        <button onClick={() => { setMode("reviews"); setPage(1); }} className={`rounded-lg px-4 py-2 text-xs font-semibold ${mode === "reviews" ? "bg-brand-50 text-brand-700" : "text-gray-500"}`}>Avis</button>
      </div>
      {error && <Alert text={error} tone="error" />}
      {mode === "faq" ? (
        <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
          <div>
            <div className="mb-3"><SearchInput value={search} onChange={(v) => { setSearch(v); setPage(1); }} placeholder="Rechercher dans la FAQ..." /></div>
            <div className="card overflow-x-auto"><table className="w-full min-w-[720px] text-sm"><thead className="table-head"><tr><th>Question</th><th>Audience</th><th>Ordre</th><th>Actions</th></tr></thead><tbody className="divide-y divide-gray-100">{faqs.map((f) => <tr key={f.id}><td className="px-4 py-3"><p className="font-semibold">{f.question}</p><p className="mt-1 line-clamp-2 text-xs text-gray-400">{f.answer || "Sans réponse"}</p></td><td className="px-4 py-3"><StatusBadge status={f.audience} /></td><td className="px-4 py-3">{f.order}</td><td className="px-4 py-3"><div className="flex gap-2"><button onClick={() => { setEditing(f); setFaqForm({ question: f.question, answer: f.answer, audience: f.audience, order: f.order }); }} className="text-xs font-semibold text-brand-700">Modifier</button><button onClick={() => deleteFaq(f.id)} className="text-xs font-semibold text-red-600">Supprimer</button></div></td></tr>)}</tbody></table>{loading && <LoadingBlock compact />}{!loading && faqs.length === 0 && <Empty text="Aucune FAQ trouvée." />}</div>
            <Pagination page={page} count={count} onPage={setPage} />
          </div>
          <form onSubmit={saveFaq} className="card self-start p-5"><h2 className="font-bold">{editing ? "Modifier la FAQ" : "Nouvelle FAQ"}</h2><div className="mt-4 space-y-3"><label className="label-admin">Question<input required className="input-admin w-full" value={faqForm.question} onChange={(e) => setFaqForm({ ...faqForm, question: e.target.value })} /></label><label className="label-admin">Réponse<textarea className="input-admin min-h-32 w-full" value={faqForm.answer} onChange={(e) => setFaqForm({ ...faqForm, answer: e.target.value })} /></label><label className="label-admin">Audience<select className="input-admin w-full" value={faqForm.audience} onChange={(e) => setFaqForm({ ...faqForm, audience: e.target.value })}><option value="all">Tout le monde</option><option value="student">Étudiants</option><option value="instructor">Instructeurs</option></select></label><label className="label-admin">Ordre<input type="number" min="0" className="input-admin w-full" value={faqForm.order} onChange={(e) => setFaqForm({ ...faqForm, order: Number(e.target.value) })} /></label><div className="flex gap-2"><button type="submit" className="btn-primary flex-1">{editing ? "Enregistrer" : "Ajouter"}</button>{editing && <button type="button" className="btn-outline" onClick={() => { setEditing(null); setFaqForm({ question: "", answer: "", audience: "all", order: 0 }); }}>Annuler</button>}</div></div></form>
        </div>
      ) : (
        <div>
          <div className="mb-3"><SearchInput value={search} onChange={(v) => { setSearch(v); setPage(1); }} placeholder="Avis, utilisateur, contenu..." /></div>
          <div className="card overflow-x-auto"><table className="w-full min-w-[820px] text-sm"><thead className="table-head"><tr><th>Utilisateur</th><th>Contenu</th><th>Note</th><th>Avis</th><th>Date</th><th></th></tr></thead><tbody className="divide-y divide-gray-100">{reviews.map((r) => <tr key={r.id}><td className="px-4 py-3 font-semibold">{r.user?.full_name || "Utilisateur"}</td><td className="px-4 py-3"><p className="font-medium">{r.target_title || "—"}</p><p className="text-xs text-gray-400">{r.target_type}</p></td><td className="px-4 py-3"><span className="inline-flex items-center gap-1 font-semibold"><Star size={14} className="text-amber-500" />{r.rating}/5</span></td><td className="max-w-[360px] px-4 py-3 text-gray-600">{r.comment || "—"}</td><td className="px-4 py-3 text-gray-500">{new Date(r.created_at).toLocaleDateString("fr-FR")}</td><td className="px-4 py-3"><button onClick={() => deleteReview(r.id)} className="text-xs font-semibold text-red-600">Supprimer</button></td></tr>)}</tbody></table>{loading && <LoadingBlock compact />}{!loading && reviews.length === 0 && <Empty text="Aucun avis trouvé." />}</div>
          <Pagination page={page} count={count} onPage={setPage} />
        </div>
      )}
    </>
  );
}

function SettingsTab() {
  const [settings, setSettings] = useState<PlatformSettings | null>(null);
  const [form, setForm] = useState<PlatformSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<PlatformSettings>("/auth/admin/platform-settings/").then((data) => { setSettings(data); setForm(data); }).catch((e) => setError(toError(e))).finally(() => setLoading(false));
  }, []);

  async function save(event: React.FormEvent) {
    event.preventDefault(); if (!form) return; setSaving(true); setError(""); setMessage("");
    try { const updated = await api.patch<PlatformSettings>("/auth/admin/platform-settings/", form); setSettings(updated); setForm(updated); setMessage("Paramètres enregistrés."); }
    catch (e) { setError(toError(e)); } finally { setSaving(false); }
  }

  if (loading) return <><PageHeader title="Paramètres de la plateforme" description="Configurez les règles globales LearnEas." /><LoadingBlock /></>;
  if (!form) return <><PageHeader title="Paramètres de la plateforme" description="Configurez les règles globales LearnEas." />{error && <Alert text={error} tone="error" />}</>;

  return (
    <>
      <PageHeader title="Paramètres de la plateforme" description="Ces valeurs sont persistées en base et appliquées à l'inscription et aux flux financiers." />
      {error && <Alert text={error} tone="error" />}{message && <Alert text={message} />}
      <form onSubmit={save} className="space-y-5">
        <section className="card p-5"><h2 className="flex items-center gap-2 font-bold"><Settings size={17} /> Identité et assistance</h2><div className="mt-4 grid gap-4 md:grid-cols-2"><label className="label-admin">Nom de la plateforme<input className="input-admin w-full" value={form.site_name} onChange={(e) => setForm({ ...form, site_name: e.target.value })} /></label><label className="label-admin">Email d'assistance<input type="email" className="input-admin w-full" value={form.support_email} onChange={(e) => setForm({ ...form, support_email: e.target.value })} /></label></div></section>
        <section className="card p-5"><h2 className="flex items-center gap-2 font-bold"><Users size={17} /> Accès et inscription</h2><div className="mt-4 grid gap-4 md:grid-cols-2"><SettingToggle title="Autoriser les nouvelles inscriptions" description="Si désactivé, l'API refuse la création de nouveaux comptes." checked={form.registration_enabled} onChange={(v) => setForm({ ...form, registration_enabled: v })} /><SettingToggle title="Autoriser les demandes instructeur" description="Contrôle la conversion d'un étudiant en instructeur depuis son espace." checked={form.instructor_applications_enabled} onChange={(v) => setForm({ ...form, instructor_applications_enabled: v })} /></div></section>
        <section className="card p-5"><h2 className="flex items-center gap-2 font-bold"><WalletCards size={17} /> Finance</h2><p className="mt-1 text-xs text-gray-500">Les nouvelles ventes utilisent immédiatement ces paramètres. Les anciennes ventes conservent leur ventilation enregistrée.</p><div className="mt-4 grid gap-4 md:grid-cols-2"><label className="label-admin">Commission plateforme (%)<input type="number" min="0" max="100" className="input-admin w-full" value={form.platform_commission_percent} onChange={(e) => setForm({ ...form, platform_commission_percent: Number(e.target.value) })} /></label><label className="label-admin">Retrait instructeur minimum (MAD)<input type="number" min="0" step="0.01" className="input-admin w-full" value={form.minimum_payout_amount} onChange={(e) => setForm({ ...form, minimum_payout_amount: e.target.value })} /></label></div></section>
        <div className="flex items-center justify-between"><p className="text-xs text-gray-400">Dernière modification : {settings?.updated_at ? new Date(settings.updated_at).toLocaleString("fr-FR") : "—"}</p><button disabled={saving} className="btn-primary" type="submit">{saving ? <><Loader2 className="animate-spin" size={15} /> Enregistrement...</> : "Enregistrer les paramètres"}</button></div>
      </form>
    </>
  );
}

function SessionReportModal({ sessionId, onClose }: { sessionId: number | null; onClose: () => void }) {
  const [report, setReport] = useState<SessionReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!sessionId) { setReport(null); setError(""); return; }
    setLoading(true); setError(""); setReport(null);
    api.get<SessionReport>(`/sessions/${sessionId}/report/`).then(setReport).catch((e) => setError(toError(e))).finally(() => setLoading(false));
  }, [sessionId]);

  return (
    <AdminModal open={!!sessionId} title={report ? `Rapport · ${report.session.formation_title} · séance ${report.session.session_number}` : "Rapport de présence"} onClose={onClose} wide>
      {loading && <LoadingBlock />}
      {error && <Alert text={error} tone="error" />}
      {report && <div>
        <div className="mb-4 grid gap-3 sm:grid-cols-3"><MiniMetric label="Durée prévue" value={`${report.session.duration_minutes} min`} /><MiniMetric label="Durée réelle" value={`${report.session.actual_duration_minutes || 0} min`} /><MiniMetric label="Participants enregistrés" value={`${report.participants.length}`} /></div>
        <div className="mb-4 rounded-xl bg-gray-50 p-3 text-sm"><span className="font-semibold">Organisateur(s) :</span> {report.organizers.map((o) => `${o.name} (${o.email})`).join(", ") || "—"}</div>
        <div className="overflow-x-auto rounded-xl border border-gray-100"><table className="w-full min-w-[760px] text-sm"><thead className="table-head"><tr><th>Participant</th><th>Rôle</th><th>Première entrée</th><th>Dernière sortie</th><th>Temps présent</th></tr></thead><tbody className="divide-y divide-gray-100">{report.participants.map((p) => <tr key={`${p.user_id}-${p.role}`}><td className="px-4 py-3"><p className="font-semibold">{p.name}</p><p className="text-xs text-gray-400">{p.email}</p></td><td className="px-4 py-3">{p.role}</td><td className="px-4 py-3 text-gray-500">{p.first_join ? new Date(p.first_join).toLocaleString("fr-FR") : "—"}</td><td className="px-4 py-3 text-gray-500">{p.last_leave ? new Date(p.last_leave).toLocaleString("fr-FR") : "Session ouverte"}</td><td className="px-4 py-3 font-semibold">{formatPresence(p.total_seconds)}</td></tr>)}{report.participants.length === 0 && <tr><td colSpan={5}><Empty text="Aucune présence enregistrée pour cette séance." /></td></tr>}</tbody></table></div>
      </div>}
    </AdminModal>
  );
}

function Kpi({ href, icon, label, value }: { href: string; icon: React.ReactNode; label: string; value: number | string }) {
  return <Link href={href} className="card group flex min-h-[94px] items-center gap-3 p-3.5 transition hover:-translate-y-0.5 hover:border-brand-100 hover:shadow-soft"><div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-brand-50 text-brand-600">{icon}</div><div className="min-w-0"><p className="truncate text-lg font-extrabold">{value}</p><p className="text-[11px] text-gray-500 group-hover:text-brand-700">{label}</p></div></Link>;
}

function CompactCard({ title, subtitle, children, footer }: { title: string; subtitle: string; children: React.ReactNode; footer: React.ReactNode }) {
  return <section className="card flex h-[310px] min-h-0 flex-col overflow-hidden"><div className="shrink-0 border-b border-gray-100 px-5 py-3.5"><h2 className="font-bold">{title}</h2><p className="text-[11px] text-gray-400">{subtitle}</p></div><div className="min-h-0 flex-1 overflow-y-auto px-5">{children}</div><div className="shrink-0 border-t border-gray-100 px-5 py-3">{footer}</div></section>;
}

function InfoCard({ label, value, note, href }: { label: string; value: string; note: string; href: string }) {
  return <Link href={href} className="card flex items-center justify-between p-4 hover:border-brand-100"><div><p className="text-xs text-gray-500">{label}</p><p className="mt-1 text-xl font-bold">{value}</p><p className="mt-1 text-[11px] text-gray-400">{note}</p></div><ArrowRight size={18} className="text-gray-300" /></Link>;
}

function MiniMetric({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl border border-gray-100 p-3"><p className="text-[11px] text-gray-400">{label}</p><p className="mt-1 font-bold">{value}</p></div>;
}

function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (value: boolean) => void; label: string }) {
  return <button type="button" onClick={() => onChange(!checked)} className="inline-flex items-center gap-2 text-xs font-medium"><span className={`relative h-5 w-9 rounded-full transition ${checked ? "bg-brand-600" : "bg-gray-200"}`}><span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition ${checked ? "left-[18px]" : "left-0.5"}`} /></span><span className={checked ? "text-brand-700" : "text-gray-500"}>{label}</span></button>;
}

function SettingToggle({ title, description, checked, onChange }: { title: string; description: string; checked: boolean; onChange: (v: boolean) => void }) {
  return <div className="rounded-xl border border-gray-100 p-4"><div className="flex items-start justify-between gap-4"><div><p className="text-sm font-semibold">{title}</p><p className="mt-1 text-xs leading-5 text-gray-500">{description}</p></div><Toggle checked={checked} onChange={onChange} label="" /></div></div>;
}

function SearchInput({ value, onChange, placeholder }: { value: string; onChange: (value: string) => void; placeholder: string }) {
  return <label className="relative min-w-[220px] flex-1 sm:max-w-sm"><Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" /><input value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder} className="input-admin w-full pl-9" /></label>;
}

function Pagination({ page, count, onPage }: { page: number; count: number; onPage: (page: number) => void }) {
  const pages = Math.max(1, Math.ceil(count / 12));
  if (pages <= 1) return null;
  return <div className="mt-4 flex items-center justify-between text-xs text-gray-500"><span>{count} résultat(s) · page {page}/{pages}</span><div className="flex gap-2"><button disabled={page <= 1} onClick={() => onPage(page - 1)} className="btn-outline !px-3 !py-1.5 disabled:opacity-40">Précédent</button><button disabled={page >= pages} onClick={() => onPage(page + 1)} className="btn-outline !px-3 !py-1.5 disabled:opacity-40">Suivant</button></div></div>;
}

function StatusBadge({ status }: { status: string }) {
  const cls = status === "paid" || status === "completed" || status === "approved" ? "bg-emerald-50 text-emerald-700" : status === "pending" || status === "processing" ? "bg-amber-50 text-amber-700" : status === "failed" || status === "cancelled" || status === "rejected" ? "bg-red-50 text-red-600" : "bg-gray-100 text-gray-600";
  return <span className={`badge ${cls}`}>{status}</span>;
}

function OrderDetails({ order, onStatus }: { order: Order; onStatus: (status: string) => void }) {
  return <div className="space-y-5"><div className="grid gap-3 sm:grid-cols-2"><MiniMetric label="Client" value={order.customer_name} /><MiniMetric label="Montant" value={formatPrice(order.total_amount)} /><MiniMetric label="Moyen" value={order.provider} /><MiniMetric label="Statut" value={order.status} /></div><div><h3 className="mb-2 text-sm font-bold">Articles</h3><div className="divide-y divide-gray-100 rounded-xl border border-gray-100">{order.items.map((i) => <div key={i.id} className="flex items-center justify-between gap-3 p-3 text-sm"><div><p className="font-semibold">{i.title}</p><p className="text-xs text-gray-400">{i.item_type} · {i.instructor_name || "Sans instructeur"}</p></div><strong>{formatPrice(i.unit_price)}</strong></div>)}</div></div><div className="rounded-xl bg-amber-50 p-3 text-xs text-amber-800">Changer le statut ici met à jour l'état interne LearnEas. Un remboursement réel auprès d'un prestataire de paiement doit être traité via son intégration lorsque celle-ci sera connectée.</div><div className="flex flex-wrap gap-2"><button onClick={() => onStatus("paid")} className="btn-primary !py-2">Marquer payée / réparer l'accès</button><button onClick={() => onStatus("failed")} className="btn-outline !py-2">Marquer échouée</button><button onClick={() => onStatus("refunded")} className="btn-outline !py-2">Marquer remboursée</button></div></div>;
}

function Alert({ text, tone = "success" }: { text: string; tone?: "success" | "error" }) {
  return <div className={`mb-4 rounded-xl border px-4 py-3 text-sm ${tone === "error" ? "border-red-100 bg-red-50 text-red-700" : "border-emerald-100 bg-emerald-50 text-emerald-700"}`}>{text}</div>;
}

function LoadingBlock({ compact = false }: { compact?: boolean }) {
  return <div className={`flex items-center justify-center gap-2 text-sm text-gray-400 ${compact ? "py-6" : "py-14"}`}><Loader2 size={17} className="animate-spin" /> Chargement...</div>;
}

function Empty({ text }: { text: string }) {
  return <div className="py-8 text-center text-sm text-gray-400">{text}</div>;
}

function formatPresence(seconds: number) {
  const total = Math.max(0, Math.round(seconds || 0));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return h > 0 ? `${h} h ${m} min` : m > 0 ? `${m} min ${s} s` : `${s} s`;
}
