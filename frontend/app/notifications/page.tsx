"use client";

import Link from "next/link";
import { Bell, CheckCheck, Loader2, Settings2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import WhatsAppPreferencesCard from "@/components/notifications/WhatsAppPreferencesCard";

type Row = {
  id: number; category: string; event_type: string; title: string; body: string; action_url: string;
  priority: string; is_read: boolean; read_at: string | null; created_at: string;
};
type ResponseData = { unread_count: number; results: Row[] };

const categories = [
  ["all", "Toutes"], ["recruitment", "Recrutement"], ["learning", "Apprentissage"],
  ["live", "Lives"], ["payment", "Paiements"], ["certificate", "Certificats"],
] as const;

export default function NotificationsPage() {
  const user = useAuth((state) => state.user);
  const hydrated = useAuth((state) => state.hydrated);
  const [rows, setRows] = useState<Row[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [filter, setFilter] = useState("all");
  const [onlyUnread, setOnlyUnread] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true); setError("");
    try {
      const params = new URLSearchParams({ limit: "100" });
      if (onlyUnread) params.set("unread", "1");
      if (filter !== "all") params.set("category", filter);
      const data = await api.get<ResponseData>(`/notifications/?${params}`);
      setRows(data.results); setUnreadCount(data.unread_count);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Impossible de charger les notifications.");
    } finally { setLoading(false); }
  }

  useEffect(() => { if (user) void load(); }, [user, filter, onlyUnread]);

  async function read(row: Row) {
    if (!row.is_read) {
      try {
        await api.post(`/notifications/${row.id}/read/`, {});
        setRows((items) => items.map((item) => item.id === row.id ? { ...item, is_read: true, read_at: new Date().toISOString() } : item));
        setUnreadCount((count) => {
          const next = Math.max(0, count - 1);
          window.dispatchEvent(new CustomEvent("kalanpro:notifications-changed", { detail: { unread_count: next } }));
          return next;
        });
      } catch { /* le lien reste utilisable */ }
    }
  }

  async function readAll() {
    await api.post("/notifications/read-all/", {});
    setUnreadCount(0);
    window.dispatchEvent(new CustomEvent("kalanpro:notifications-changed", { detail: { unread_count: 0 } }));
    setRows((items) => items.map((row) => ({ ...row, is_read: true, read_at: row.read_at || new Date().toISOString() })));
  }

  const heading = useMemo(() => categories.find(([key]) => key === filter)?.[1] || "Toutes", [filter]);

  if (!hydrated) return <main className="container-app py-16"><div className="card mx-auto max-w-xl p-8 text-center text-sm text-gray-500">Chargement de votre session...</div></main>;
  if (!user) return <main className="container-app py-16"><div className="card mx-auto max-w-xl p-8 text-center"><Bell className="mx-auto text-gray-300" size={34}/><h1 className="mt-3 text-xl font-bold">Connectez-vous pour voir vos notifications</h1><p className="mt-2 text-sm text-gray-500">Votre centre KalanPro est privé et lié à votre compte.</p><Link href="/login?next=%2Fnotifications" className="btn-primary mt-5">Se connecter</Link></div></main>;

  return (
    <main className="container-app py-10">
      <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div><div className="flex items-center gap-2"><Bell className="text-brand-500" size={24}/><h1 className="text-2xl font-black">Centre de notifications</h1></div><p className="mt-1 text-sm text-gray-500">Paiements, apprentissage, lives et recrutement dans un seul historique.</p></div>
        {unreadCount > 0 && <button type="button" onClick={() => void readAll()} className="btn-outline !py-2"><CheckCheck size={15}/> Tout marquer comme lu</button>}
      </div>

      <div className="mb-5 flex flex-wrap items-center gap-2">
        {categories.map(([key, label]) => <button key={key} type="button" onClick={() => setFilter(key)} className={`rounded-full px-3 py-2 text-xs font-bold ${filter === key ? "bg-navy-950 text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"}`}>{label}</button>)}
        <label className="ml-auto flex items-center gap-2 rounded-full border border-gray-200 px-3 py-2 text-xs font-semibold text-gray-600"><input type="checkbox" checked={onlyUnread} onChange={(e) => setOnlyUnread(e.target.checked)} className="accent-brand-600"/> Non lues seulement</label>
      </div>

      <section className="card overflow-hidden">
        <div className="flex items-center justify-between border-b border-gray-100 px-5 py-4"><div><h2 className="font-bold">{heading}</h2><p className="text-xs text-gray-400">{unreadCount} notification{unreadCount > 1 ? "s" : ""} non lue{unreadCount > 1 ? "s" : ""}</p></div></div>
        {loading ? <div className="flex items-center gap-2 px-5 py-8 text-sm text-gray-400"><Loader2 size={16} className="animate-spin"/> Chargement...</div> : error ? <p className="px-5 py-8 text-sm text-red-600">{error}</p> : rows.length === 0 ? <div className="px-5 py-12 text-center text-sm text-gray-400">Aucune notification dans cette catégorie.</div> : <div className="divide-y divide-gray-100">
          {rows.map((row) => {
            const content = <div className={`flex gap-4 px-5 py-4 ${row.is_read ? "bg-white" : "bg-orange-50/40"}`}><span className={`mt-1 h-2.5 w-2.5 shrink-0 rounded-full ${row.is_read ? "bg-gray-200" : row.priority === "high" ? "bg-red-500" : "bg-brand-500"}`}/><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h3 className="font-bold">{row.title}</h3><span className="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-gray-500">{row.category}</span></div>{row.body && <p className="mt-1 text-sm leading-6 text-gray-600">{row.body}</p>}<p className="mt-2 text-[11px] text-gray-400">{new Date(row.created_at).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short" })}</p></div></div>;
            return row.action_url ? <a key={row.id} href={row.action_url} onClick={() => void read(row)} className="block hover:bg-gray-50">{content}</a> : <button key={row.id} type="button" onClick={() => void read(row)} className="block w-full text-left">{content}</button>;
          })}
        </div>}
      </section>

      <div className="mt-8"><div className="mb-3 flex items-center gap-2"><Settings2 size={18} className="text-brand-500"/><h2 className="text-lg font-bold">Préférences multicanal</h2></div><WhatsAppPreferencesCard /></div>
      <p className="mt-4 text-xs text-gray-400">Les alertes de sécurité essentielles peuvent utiliser des mécanismes dédiés indépendamment de ces préférences.</p>
    </main>
  );
}
