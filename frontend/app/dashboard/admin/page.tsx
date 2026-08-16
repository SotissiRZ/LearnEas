"use client";

import { useEffect, useState } from "react";
import { ExternalLink, ShoppingBag, BookOpen, FileText, DollarSign } from "lucide-react";
import { api, formatPrice } from "@/lib/api";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import DashboardNav from "@/components/dashboard/DashboardNav";
import GuardScreen from "@/components/ui/GuardScreen";

interface Order {
  id: number;
  status: string;
  total_amount: string;
  invoice_number: string;
  created_at: string;
  items: { title: string; item_type: string }[];
}

export default function AdminDashboard() {
  const { ready } = useAuthGuard({ roles: ["admin"], redirectTo: "/" });
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ready) return;
    api.get<{ results: Order[] } | Order[]>("/payments/orders/")
      .then((d: any) => setOrders(d.results || d))
      .finally(() => setLoading(false));
  }, [ready]);

  if (!ready) return <GuardScreen />;

  const revenue = orders.filter((o) => o.status === "paid").reduce((sum, o) => sum + parseFloat(o.total_amount), 0);

  return (
    <div className="container-app py-10">
      <DashboardNav role="admin" />

      <div className="mb-8 flex items-center justify-between">
        <h1 className="text-xl font-bold">Vue d'ensemble</h1>
        <a
          href={(process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api").replace("/api", "/admin")}
          target="_blank" rel="noreferrer" className="btn-outline !py-2 !text-sm"
        >
          Administration Django <ExternalLink size={14} />
        </a>
      </div>

      <div className="mb-10 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat icon={<DollarSign size={20} />} label="Revenu total" value={formatPrice(revenue)} />
        <Stat icon={<ShoppingBag size={20} />} label="Commandes" value={orders.length} />
        <Stat icon={<BookOpen size={20} />} label="Commandes cours" value={orders.filter((o) => o.items.some((i) => i.item_type === "course")).length} />
        <Stat icon={<FileText size={20} />} label="Commandes PDF" value={orders.filter((o) => o.items.some((i) => i.item_type === "pdf")).length} />
      </div>

      <h2 className="mb-4 text-lg font-bold">Dernières commandes</h2>
      {loading ? (
        <p className="text-gray-500">Chargement...</p>
      ) : orders.length === 0 ? (
        <p className="text-gray-500">Aucune commande pour le moment.</p>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3">Facture</th>
                <th className="px-4 py-3">Articles</th>
                <th className="px-4 py-3">Montant</th>
                <th className="px-4 py-3">Statut</th>
                <th className="px-4 py-3">Date</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {orders.slice(0, 15).map((o) => (
                <tr key={o.id}>
                  <td className="px-4 py-3 font-mono text-xs">{o.invoice_number}</td>
                  <td className="px-4 py-3">{o.items.map((i) => i.title).join(", ")}</td>
                  <td className="px-4 py-3 font-semibold">{formatPrice(o.total_amount)}</td>
                  <td className="px-4 py-3">
                    <span className={`badge ${o.status === "paid" ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-600"}`}>
                      {o.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500">{new Date(o.created_at).toLocaleDateString("fr-FR")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: number | string }) {
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
