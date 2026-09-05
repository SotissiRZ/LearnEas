"use client";

import Link from "next/link";
import { Bell, BriefcaseBusiness, CheckCheck, GraduationCap, ReceiptText, Radio, Award } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

type NotificationRow = {
  id: number;
  category: string;
  event_type: string;
  title: string;
  body: string;
  action_url: string;
  priority: "low" | "normal" | "high";
  is_read: boolean;
  read_at: string | null;
  created_at: string;
};

type NotificationResponse = { unread_count: number; results: NotificationRow[] };

function iconFor(category: string) {
  if (category === "recruitment") return <BriefcaseBusiness size={15} />;
  if (category === "payment") return <ReceiptText size={15} />;
  if (category === "live" || category === "mentorship") return <Radio size={15} />;
  if (category === "certificate") return <Award size={15} />;
  return <GraduationCap size={15} />;
}

export default function NotificationBell() {
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState<NotificationRow[]>([]);
  const [unread, setUnread] = useState(0);
  const rootRef = useRef<HTMLDivElement | null>(null);

  async function refresh(withRows = false) {
    try {
      if (withRows) {
        const data = await api.get<NotificationResponse>("/notifications/?limit=8");
        setRows(data.results);
        setUnread(data.unread_count);
      } else {
        const data = await api.get<{ unread_count: number }>("/notifications/unread-count/");
        setUnread(data.unread_count);
      }
    } catch {
      // Le badge ne doit jamais casser la navigation si le backend est momentanément indisponible.
    }
  }

  useEffect(() => {
    void refresh(false);
    const timer = window.setInterval(() => void refresh(false), 60_000);
    const onFocus = () => void refresh(false);
    const onChanged = (event: Event) => {
      const detail = (event as CustomEvent<{ unread_count?: number }>).detail;
      if (typeof detail?.unread_count === "number") setUnread(Math.max(0, detail.unread_count));
      else void refresh(false);
    };
    window.addEventListener("focus", onFocus);
    window.addEventListener("kalanpro:notifications-changed", onChanged);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", onFocus);
      window.removeEventListener("kalanpro:notifications-changed", onChanged);
    };
  }, []);

  useEffect(() => {
    function outside(event: MouseEvent) {
      if (open && rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(false);
    }
    function escape(event: KeyboardEvent) { if (event.key === "Escape") setOpen(false); }
    document.addEventListener("mousedown", outside);
    document.addEventListener("keydown", escape);
    return () => {
      document.removeEventListener("mousedown", outside);
      document.removeEventListener("keydown", escape);
    };
  }, [open]);

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (next) await refresh(true);
  }

  async function markRead(row: NotificationRow) {
    if (!row.is_read) {
      try {
        await api.post(`/notifications/${row.id}/read/`, {});
        setRows((items) => items.map((item) => item.id === row.id ? { ...item, is_read: true, read_at: new Date().toISOString() } : item));
        setUnread((value) => {
          const next = Math.max(0, value - 1);
          window.dispatchEvent(new CustomEvent("kalanpro:notifications-changed", { detail: { unread_count: next } }));
          return next;
        });
      } catch { /* navigation reste possible */ }
    }
    setOpen(false);
  }

  async function markAll() {
    try {
      await api.post("/notifications/read-all/", {});
      setRows((items) => items.map((item) => ({ ...item, is_read: true, read_at: item.read_at || new Date().toISOString() })));
      setUnread(0);
      window.dispatchEvent(new CustomEvent("kalanpro:notifications-changed", { detail: { unread_count: 0 } }));
    } catch { /* no-op */ }
  }

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        onClick={() => void toggle()}
        className="relative rounded-xl p-2.5 text-white/80 transition hover:bg-white/10 hover:text-white"
        aria-label={unread ? `${unread} notification${unread > 1 ? "s" : ""} non lue${unread > 1 ? "s" : ""}` : "Notifications"}
        aria-expanded={open}
      >
        <Bell size={20} />
        {unread > 0 && (
          <span className="absolute -right-1 -top-1 grid h-5 min-w-5 place-items-center rounded-full bg-brand-500 px-1 text-[10px] font-black text-white">
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-12 w-[min(92vw,390px)] overflow-hidden rounded-2xl border border-slate-200 bg-white text-ink shadow-soft">
          <div className="flex items-center justify-between gap-3 border-b border-slate-100 px-4 py-3">
            <div><p className="font-bold">Notifications</p><p className="text-[11px] text-slate-400">{unread} non lue{unread > 1 ? "s" : ""}</p></div>
            {unread > 0 && <button type="button" onClick={() => void markAll()} className="inline-flex items-center gap-1 text-[11px] font-bold text-brand-600"><CheckCheck size={13}/> Tout lire</button>}
          </div>
          <div className="max-h-[420px] overflow-y-auto">
            {rows.length === 0 ? (
              <div className="px-5 py-10 text-center text-sm text-slate-400">Aucune notification pour le moment.</div>
            ) : rows.map((row) => {
              const content = (
                <div className={`flex gap-3 px-4 py-3 transition hover:bg-slate-50 ${row.is_read ? "" : "bg-orange-50/50"}`}>
                  <span className={`mt-0.5 grid h-8 w-8 shrink-0 place-items-center rounded-lg ${row.is_read ? "bg-slate-100 text-slate-500" : "bg-brand-100 text-brand-700"}`}>{iconFor(row.category)}</span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-start gap-2"><p className="line-clamp-1 flex-1 text-sm font-bold">{row.title}</p>{!row.is_read && <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-brand-500" />}</div>
                    {row.body && <p className="mt-0.5 line-clamp-2 text-xs leading-5 text-slate-500">{row.body}</p>}
                    <p className="mt-1 text-[10px] text-slate-400">{new Date(row.created_at).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" })}</p>
                  </div>
                </div>
              );
              return row.action_url ? <a key={row.id} href={row.action_url} onClick={() => void markRead(row)}>{content}</a> : <button key={row.id} type="button" onClick={() => void markRead(row)} className="block w-full text-left">{content}</button>;
            })}
          </div>
          <Link href="/notifications" onClick={() => setOpen(false)} className="block border-t border-slate-100 px-4 py-3 text-center text-xs font-black text-brand-600 hover:bg-slate-50">Voir toutes les notifications</Link>
        </div>
      )}
    </div>
  );
}
