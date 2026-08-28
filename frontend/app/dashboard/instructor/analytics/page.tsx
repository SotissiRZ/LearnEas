"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { BarChart3, TrendingUp, ShoppingBag, WalletCards, ArrowRight } from "lucide-react";
import { api, ApiError, formatPrice } from "@/lib/api";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import GuardScreen from "@/components/ui/GuardScreen";

interface FinanceSummary {
  gross_revenue: string; total_earnings: string; available_balance: string; paid_out: string; sales_count: number;
  monthly_revenue: { month: string; gross: string; earning: string; sales: number }[];
  top_content: { id: number; type: "course" | "pdf" | "formation"; title: string; sales: number; gross: string; earning: string }[];
}

export default function InstructorAnalyticsPage() {
  const { ready } = useAuthGuard({ roles: ["instructor", "admin"], redirectTo: "/dashboard/instructor" });
  const [data, setData] = useState<FinanceSummary | null>(null);
  const [error, setError] = useState("");

  useEffect(() => { if (ready) api.get<FinanceSummary>("/payments/instructor/finance/").then(setData).catch((e) => setError(e instanceof ApiError ? e.message : "Impossible de charger les statistiques.")); }, [ready]);
  const maxRevenue = useMemo(() => Math.max(1, ...(data?.monthly_revenue || []).map((m) => Number(m.earning))), [data]);

  if (!ready) return <GuardScreen />;
  return <div className="min-w-0">
    <div className="mb-6"><h1 className="text-xl font-bold">Statistiques</h1><p className="mt-1 text-sm text-gray-500">Analysez vos ventes et identifiez les contenus qui performent le mieux.</p></div>
    {error && <div className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</div>}
    <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Stat icon={<TrendingUp size={18} />} label="Chiffre d'affaires" value={formatPrice(data?.gross_revenue || 0)} />
      <Stat icon={<WalletCards size={18} />} label="Vos gains" value={formatPrice(data?.total_earnings || 0)} />
      <Stat icon={<ShoppingBag size={18} />} label="Ventes payées" value={data?.sales_count || 0} />
      <Stat icon={<BarChart3 size={18} />} label="Solde disponible" value={formatPrice(data?.available_balance || 0)} />
    </div>

    <div className="mb-6 grid gap-5 xl:grid-cols-[1.2fr_.8fr]">
      <div className="card p-5">
        <div className="mb-4"><h2 className="font-bold">Évolution des gains</h2><p className="text-xs text-gray-500">Votre part nette, par mois</p></div>
        <div className="flex h-64 items-end gap-3 overflow-x-auto border-b border-gray-100 pb-2">
          {(data?.monthly_revenue || []).slice(-12).map((m) => { const value = Number(m.earning); const height = Math.max(6, (value / maxRevenue) * 190); return <div key={m.month} className="flex min-w-[56px] flex-1 flex-col items-center gap-2"><span className="text-[10px] font-semibold text-gray-500">{formatPrice(value)}</span><div className="w-full max-w-10 rounded-t-lg bg-brand-500" style={{ height }} title={`${m.sales} vente(s)`} /><span className="text-[10px] text-gray-400">{new Date(m.month).toLocaleDateString("fr-FR", { month: "short", year: "2-digit" })}</span></div>; })}
          {!data?.monthly_revenue?.length && <div className="m-auto text-sm text-gray-400">Aucune vente payée à analyser.</div>}
        </div>
      </div>

      <div className="card p-5">
        <div className="mb-4"><h2 className="font-bold">Répartition rapide</h2><p className="text-xs text-gray-500">Résumé financier</p></div>
        <div className="space-y-3"><Line label="Déjà versé" value={formatPrice(data?.paid_out || 0)} /><Line label="Disponible" value={formatPrice(data?.available_balance || 0)} /><Line label="Gains cumulés" value={formatPrice(data?.total_earnings || 0)} /></div>
        <Link href="/dashboard/instructor/finance" className="mt-5 inline-flex items-center gap-1 text-xs font-semibold text-brand-700">Gérer mes versements <ArrowRight size={13} /></Link>
      </div>
    </div>

    <div className="card overflow-hidden">
      <div className="border-b border-gray-100 p-5"><h2 className="font-bold">Contenus les plus performants</h2><p className="text-xs text-gray-500">Classement par nombre de ventes</p></div>
      <div className="overflow-x-auto"><table className="w-full min-w-[640px] text-sm"><thead className="bg-gray-50 text-left text-xs text-gray-500"><tr><th className="px-4 py-3">Contenu</th><th className="px-4 py-3">Type</th><th className="px-4 py-3">Ventes</th><th className="px-4 py-3">CA</th><th className="px-4 py-3">Vos gains</th></tr></thead><tbody className="divide-y divide-gray-100">{(data?.top_content || []).map((r) => <tr key={`${r.type}-${r.id}`}><td className="px-4 py-3 font-semibold">{r.title}</td><td className="px-4 py-3"><span className="badge bg-gray-100 text-gray-700">{r.type === "course" ? "Cours" : r.type === "pdf" ? "PDF" : "Formation"}</span></td><td className="px-4 py-3">{r.sales}</td><td className="px-4 py-3">{formatPrice(r.gross)}</td><td className="px-4 py-3 font-semibold text-brand-700">{formatPrice(r.earning)}</td></tr>)}{!data?.top_content?.length && <tr><td colSpan={5} className="px-4 py-8 text-center text-gray-400">Aucune donnée disponible.</td></tr>}</tbody></table></div>
    </div>
  </div>;
}
function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: string | number }) { return <div className="card flex items-center gap-3 p-4"><span className="grid h-10 w-10 place-items-center rounded-xl bg-brand-50 text-brand-700">{icon}</span><div><p className="text-lg font-extrabold">{value}</p><p className="text-xs text-gray-500">{label}</p></div></div>; }
function Line({ label, value }: { label: string; value: string }) { return <div className="flex items-center justify-between rounded-xl bg-gray-50 px-4 py-3"><span className="text-sm text-gray-500">{label}</span><strong>{value}</strong></div>; }
