"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { PlayCircle, Award, Clock, BookOpen, CreditCard, Loader2, RefreshCw, ClipboardCheck, BriefcaseBusiness, ArrowRight, Crown } from "lucide-react";
import { api, formatDuration, ApiError } from "@/lib/api";
import { CourseEnrollment } from "@/types";
import ProgressBar from "@/components/ui/ProgressBar";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import DashboardNav from "@/components/dashboard/DashboardNav";
import GuardScreen from "@/components/ui/GuardScreen";



type PremiumStatus = {
  active: boolean;
  starts_at: string | null;
  current_period_ends_at: string | null;
  coverage_ends_at: string | null;
  renewal: {
    enabled: boolean;
    status: "scheduled" | "action_required" | "past_due" | "paused" | "cancelled";
    provider: string | null;
    currency: string | null;
    next_renewal_at: string | null;
    grace_ends_at: string | null;
    last_attempt_at: string | null;
    failure_count: number;
    action_url: string | null;
    recurring_mode: string | null;
    automatic_charge: boolean;
  };
};

type StudentOrder = {
  id: number;
  status: "pending" | "paid" | "failed" | "refunded";
  provider: string;
  base_total_amount: string;
  total_amount: string;
  currency: string;
  invoice_number: string;
  created_at: string;
};

export default function StudentDashboard() {
  const { ready } = useAuthGuard();
  const searchParams = useSearchParams();
  const [enrollments, setEnrollments] = useState<CourseEnrollment[]>([]);
  const [orders, setOrders] = useState<StudentOrder[]>([]);
  const [premium, setPremium] = useState<PremiumStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [checkingOrderId, setCheckingOrderId] = useState<number | null>(null);
  const [paymentMessage, setPaymentMessage] = useState("");
  const [renewalBusy, setRenewalBusy] = useState(false);
  const autoConfirmedRef = useRef<number | null>(null);

  const loadData = useCallback(async () => {
    const [courseData, orderData, premiumData] = await Promise.all([
      api.get<{ results: CourseEnrollment[] } | CourseEnrollment[]>("/enrollments/my-courses/"),
      api.get<{ results: StudentOrder[] } | StudentOrder[]>("/payments/orders/?ordering=-created_at&page_size=10"),
      api.get<PremiumStatus>("/payments/premium/").catch(() => null),
    ]);
    setEnrollments(Array.isArray(courseData) ? courseData : courseData.results);
    setOrders(Array.isArray(orderData) ? orderData : orderData.results);
    setPremium(premiumData);
  }, []);

  const verifyOrder = useCallback(async (orderId: number, automatic = false) => {
    setCheckingOrderId(orderId);
    if (!automatic) setPaymentMessage("");
    try {
      await api.post(`/payments/orders/${orderId}/confirm/`, {});
      setPaymentMessage("Paiement vérifié. Vos accès ont été actualisés.");
      await loadData();
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Impossible de vérifier le paiement pour le moment.";
      if (!automatic || !message.toLowerCase().includes("pas encore")) setPaymentMessage(message);
    } finally {
      setCheckingOrderId(null);
    }
  }, [loadData]);


  const updatePremiumRenewal = useCallback(async (enabled: boolean) => {
    setRenewalBusy(true);
    setPaymentMessage("");
    try {
      const renewal = await api.patch<PremiumStatus["renewal"]>("/payments/premium/renewal/", { enabled });
      setPremium((current) => current ? { ...current, renewal } : current);
      setPaymentMessage(enabled
        ? "Renouvellement Premium planifié. KalanPro préparera le prochain paiement avant l’échéance."
        : "Renouvellement Premium désactivé. Votre période déjà payée reste active jusqu’à son échéance.");
    } catch (error) {
      setPaymentMessage(error instanceof ApiError ? error.message : "Impossible de modifier le renouvellement Premium.");
    } finally {
      setRenewalBusy(false);
    }
  }, []);

  useEffect(() => {
    if (!ready) return;
    loadData().catch(() => {}).finally(() => setLoading(false));
  }, [ready, loadData]);

  useEffect(() => {
    if (!ready) return;
    const raw = searchParams.get("order");
    const orderId = raw ? Number(raw) : NaN;
    if (!Number.isInteger(orderId) || orderId <= 0 || autoConfirmedRef.current === orderId) return;
    autoConfirmedRef.current = orderId;
    void verifyOrder(orderId, true);
  }, [ready, searchParams, verifyOrder]);

  if (!ready) return <GuardScreen />;

  const inProgress = enrollments.filter((e) => !e.completed);
  const completed = enrollments.filter((e) => e.completed);

  return (
    <div className="container-app py-10">
      <DashboardNav role="student" />

      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Stat icon={<BookOpen size={20} />} label="Cours accessibles" value={enrollments.length} />
        <Stat icon={<Clock size={20} />} label="En cours" value={inProgress.length} />
        <Stat icon={<Award size={20} />} label="Terminés" value={completed.length} />
      </div>

      {paymentMessage && <div className="mb-5 rounded-xl border border-brand-100 bg-brand-50 px-4 py-3 text-sm text-brand-800">{paymentMessage}</div>}

      {premium?.active && (
        <section className="mb-8 overflow-hidden rounded-2xl border border-violet-200 bg-gradient-to-r from-violet-50 to-white p-5 shadow-card">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
              <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-violet-600 text-white"><Crown size={20} /></span>
              <div><p className="font-extrabold text-violet-950">KalanPro Premium actif</p><p className="mt-1 text-xs leading-5 text-violet-700">Accès au catalogue Premium jusqu’au {premium.coverage_ends_at ? new Date(premium.coverage_ends_at).toLocaleDateString("fr-FR") : "prochain renouvellement"}. Vos achats à l’unité restent permanents.</p>{premium.renewal?.enabled && <p className="mt-1 text-[11px] font-semibold text-violet-800">Renouvellement planifié · le paiement sera préparé avant l’échéance et devra être confirmé auprès du prestataire tant qu’aucun mandat hors session n’est disponible.</p>}</div>
            </div>
            <div className="flex shrink-0 flex-wrap gap-2"><Link href="/courses?premium_included=true" className="btn-primary !py-2 !text-xs">Cours Premium</Link><Link href="/pdfs?premium_included=true" className="btn-outline !py-2 !text-xs">PDF Premium</Link><Link href="/checkout?learner_product=premium" className="btn-outline !py-2 !text-xs">Prolonger 30 jours</Link><button type="button" disabled={renewalBusy} onClick={() => void updatePremiumRenewal(!premium.renewal?.enabled)} className="btn-outline !py-2 !text-xs">{renewalBusy ? "Mise à jour…" : premium.renewal?.enabled ? "Désactiver renouvellement" : "Planifier renouvellement"}</button>{premium.renewal?.action_url && <a href={premium.renewal.action_url} className="btn-primary !py-2 !text-xs">Confirmer le renouvellement</a>}{premium.renewal?.status === "past_due" && premium.renewal.grace_ends_at && <p className="basis-full text-xs text-amber-700">Fenêtre de rattrapage jusqu’au {new Date(premium.renewal.grace_ends_at).toLocaleString("fr-FR")}. L’accès Premium n’est pas prolongé pendant ce délai.</p>}</div>
          </div>
        </section>
      )}

      <div className="mb-8 grid gap-4 md:grid-cols-2">
        <Link href="/dashboard/student/projects" className="card group flex items-center gap-4 p-5 transition hover:-translate-y-0.5 hover:shadow-soft"><span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-violet-50 text-violet-700"><ClipboardCheck size={20}/></span><div className="min-w-0 flex-1"><p className="font-bold">Projets pratiques</p><p className="mt-1 text-xs text-gray-500">Appliquez vos cours sur des livrables corrigés par vos instructeurs.</p></div><ArrowRight size={16} className="text-gray-300 transition group-hover:text-brand-600"/></Link>
        <Link href="/dashboard/student/portfolio" className="card group flex items-center gap-4 p-5 transition hover:-translate-y-0.5 hover:shadow-soft"><span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-emerald-50 text-emerald-700"><BriefcaseBusiness size={20}/></span><div className="min-w-0 flex-1"><p className="font-bold">Portfolio professionnel</p><p className="mt-1 text-xs text-gray-500">Présentez vos projets validés aux recruteurs et clients.</p></div><ArrowRight size={16} className="text-gray-300 transition group-hover:text-brand-600"/></Link>
      </div>

      {orders.length > 0 && (
        <section className="card mb-8 overflow-hidden">
          <div className="flex items-center justify-between border-b border-gray-100 px-4 py-3">
            <div><h2 className="flex items-center gap-2 font-bold"><CreditCard size={17} /> Mes commandes récentes</h2><p className="mt-0.5 text-xs text-gray-500">Les paiements externes sont toujours revérifiés côté serveur avant d'accorder un accès.</p></div>
          </div>
          <div className="overflow-x-auto"><table className="w-full min-w-[680px] text-sm"><thead className="table-head"><tr><th>Commande</th><th>Prestataire</th><th>Montant</th><th>Statut</th><th>Date</th><th></th></tr></thead><tbody className="divide-y divide-gray-100">{orders.map(order => <tr key={order.id}><td className="px-4 py-3 font-semibold">{order.invoice_number}</td><td className="px-4 py-3 capitalize">{order.provider}</td><td className="px-4 py-3">{Number(order.total_amount).toLocaleString("fr-FR")} {order.currency}</td><td className="px-4 py-3"><span className={`badge ${order.status === "paid" ? "bg-emerald-50 text-emerald-700" : order.status === "pending" ? "bg-amber-50 text-amber-700" : "bg-gray-100 text-gray-600"}`}>{order.status === "paid" ? "Payée" : order.status === "pending" ? "En attente" : order.status}</span></td><td className="px-4 py-3 text-xs text-gray-500">{new Date(order.created_at).toLocaleString("fr-FR")}</td><td className="px-4 py-3 text-right">{order.status === "pending" && order.provider !== "manual" && <button type="button" onClick={() => void verifyOrder(order.id)} disabled={checkingOrderId === order.id} className="btn-outline !py-1.5 !text-xs">{checkingOrderId === order.id ? <Loader2 size={13} className="animate-spin" /> : <RefreshCw size={13} />} Vérifier</button>}</td></tr>)}</tbody></table></div>
        </section>
      )}

      <h2 className="mb-4 text-xl font-bold">Mes cours</h2>
      {loading ? (
        <p className="text-gray-500">Chargement...</p>
      ) : enrollments.length === 0 ? (
        <div className="card p-10 text-center text-gray-500">
          Vous n'avez pas encore de cours. <Link href="/courses" className="font-semibold text-brand-700">Explorer le catalogue</Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {enrollments.map((e) => (
            <div key={e.id} className="card overflow-hidden transition hover:-translate-y-1 hover:shadow-soft">
              <Link href={`/learn/${e.course.slug}`} className="block">
                <div className="aspect-video bg-gradient-to-br from-brand-100 to-brand-50">
                  {e.course.thumbnail && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img loading="lazy" decoding="async" src={e.course.thumbnail} alt={e.course.title} className="h-full w-full object-cover" />
                  )}
                </div>
                <div className="p-4 pb-0">
                  <h3 className="line-clamp-2 font-bold">{e.course.title}</h3>
                  <p className="mt-1 text-xs text-gray-500">{formatDuration(e.course.total_duration_minutes)} · {e.course.total_lessons} vidéos</p>
                  {e.access_expires_at && <p className="mt-1 text-[11px] font-semibold text-violet-700">Premium · accès jusqu’au {new Date(e.access_expires_at).toLocaleDateString("fr-FR")}</p>}
                  <div className="mt-3">
                    <div className="mb-1 flex justify-between text-xs text-gray-500">
                      <span>{e.progress_percent}% terminé</span>
                      {e.completed && <span className="flex items-center gap-1 text-brand-700"><Award size={12} /> Certifié</span>}
                    </div>
                    <ProgressBar value={e.progress_percent} />
                  </div>
                </div>
              </Link>
              <div className="p-4 pt-4">
                <Link href={`/learn/${e.course.slug}`} className="btn-primary w-full !py-2 !text-sm">
                  <PlayCircle size={16} /> {e.progress_percent > 0 ? "Continuer" : "Commencer"}
                </Link>
                {e.certificate_issued && (
                  <Link
                    href={`/certificate/${e.id}`}
                    className="btn-outline mt-2 w-full !py-2 !text-sm !border-amber-400 !text-amber-700"
                  >
                    <Award size={16} /> Voir le certificat
                  </Link>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
  return (
    <div className="card flex items-center gap-3 p-4">
      <div className="grid h-11 w-11 place-items-center rounded-xl bg-brand-50 text-brand-600">{icon}</div>
      <div>
        <p className="text-xl font-extrabold">{value}</p>
        <p className="text-xs text-gray-500">{label}</p>
      </div>
    </div>
  );
}
