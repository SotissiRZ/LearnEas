"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import type { PointerEvent as ReactPointerEvent } from "react";
import {
  Bot, ChevronLeft, ExternalLink, History, Loader2, Maximize2, MessageSquarePlus,
  Minimize2, Send, Sparkles, Trash2, X, ThumbsUp, ThumbsDown, Check, Ban, ShieldCheck, Wrench,
  Paperclip, FileText, Image as ImageIcon,
} from "lucide-react";
import { api, ApiError, apiUploadWithProgress, apiDownload } from "@/lib/api";
import { AI_CONTEXT_EVENT, AIPageContext, currentAIContext, inferAIContext } from "@/lib/aiContext";
import { useAuth } from "@/hooks/useAuth";
import type { AIAction, AIAttachment, AIConversation, AIMessage, AIQuota, AIStatus } from "@/types";

type Props = { embedded?: boolean; panelActions?: ReactNode };
type ChatResult = { conversation_id: number; message: AIMessage; quota: AIQuota; context: Record<string, unknown>; attachments?: AIAttachment[] };

function unwrap<T>(value: { results?: T[] } | T[]): T[] {
  return Array.isArray(value) ? value : value.results || [];
}

export function AssistantWorkspace({ embedded = false, panelActions }: Props) {
  const pathname = usePathname();
  const { user, hydrated } = useAuth();
  const [status, setStatus] = useState<AIStatus | null>(null);
  const [conversations, setConversations] = useState<AIConversation[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [messages, setMessages] = useState<AIMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [style, setStyle] = useState<"short" | "normal" | "detailed">("normal");
  const [busy, setBusy] = useState(false);
  const [loadingConversation, setLoadingConversation] = useState(false);
  const [error, setError] = useState("");
  const [pendingAttachments, setPendingAttachments] = useState<AIAttachment[]>([]);
  const [uploadingAttachment, setUploadingAttachment] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [pageContext, setPageContext] = useState<AIPageContext>(() => currentAIContext(pathname));
  const endRef = useRef<HTMLDivElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => setPageContext(currentAIContext(pathname)), [pathname]);
  useEffect(() => {
    const listener = (event: Event) => {
      const detail = (event as CustomEvent<AIPageContext>).detail || {};
      setPageContext({ ...inferAIContext(window.location.pathname), ...detail, path: window.location.pathname });
    };
    window.addEventListener(AI_CONTEXT_EVENT, listener as EventListener);
    return () => window.removeEventListener(AI_CONTEXT_EVENT, listener as EventListener);
  }, []);

  useEffect(() => {
    if (!hydrated || !user) return;
    api.get<AIStatus>("/ai/status/").then(async (s) => {
      setStatus(s);
      if (!s.history_enabled) {
        setConversations([]);
        return;
      }
      const c = await api.get<{ results?: AIConversation[] } | AIConversation[]>("/ai/conversations/?archived=false");
      setConversations(unwrap(c));
    }).catch((e) => setError(e instanceof ApiError ? e.message : "Assistant indisponible."));
  }, [hydrated, user]);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, busy]);

  function discardPendingAttachments() {
    const rows = pendingAttachments;
    setPendingAttachments([]);
    rows.forEach((row) => { void api.del(`/ai/attachments/${row.id}/`).catch(() => undefined); });
  }

  async function uploadFiles(fileList: FileList | File[]) {
    if (!status?.attachments_enabled || uploadingAttachment) return;
    const maxCount = status.max_attachments_per_message || 5;
    const available = Math.max(0, maxCount - pendingAttachments.length);
    const files = Array.from(fileList).slice(0, available);
    if (!files.length) {
      setError(`Maximum ${maxCount} fichiers par message.`);
      return;
    }
    setUploadingAttachment(true); setError(""); setUploadProgress(0);
    try {
      for (const file of files) {
        const maxBytes = (status.max_attachment_mb || 12) * 1024 * 1024;
        if (file.size > maxBytes) throw new ApiError(`${file.name} dépasse la limite de ${status.max_attachment_mb || 12} Mo.`);
        const form = new FormData();
        form.append("file", file);
        if (activeId) form.append("conversation_id", String(activeId));
        const row = await apiUploadWithProgress<AIAttachment>("/ai/attachments/", form, setUploadProgress);
        setPendingAttachments((current) => [...current, row]);
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Le fichier n'a pas pu être chargé.");
    } finally {
      setUploadingAttachment(false); setUploadProgress(0);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function removePendingAttachment(row: AIAttachment) {
    setPendingAttachments((current) => current.filter((item) => item.id !== row.id));
    try { await api.del(`/ai/attachments/${row.id}/`); } catch { /* suppression locale suffisante pour l'UX */ }
  }

  async function openConversation(id: number) {
    discardPendingAttachments();
    setLoadingConversation(true); setError("");
    try {
      const value = await api.get<AIConversation>(`/ai/conversations/${id}/`);
      setActiveId(id); setMessages(value.messages || []);
    } catch (e) { setError(e instanceof ApiError ? e.message : "Conversation indisponible."); }
    finally { setLoadingConversation(false); }
  }

  function newConversation() { discardPendingAttachments(); setActiveId(null); setMessages([]); setDraft(""); setError(""); }

  async function removeConversation(id: number) {
    if (!confirm("Supprimer cette conversation IA ?")) return;
    try {
      await api.del(`/ai/conversations/${id}/`);
      setConversations((rows) => rows.filter((row) => row.id !== id));
      if (activeId === id) newConversation();
    } catch (e) { setError(e instanceof ApiError ? e.message : "Suppression impossible."); }
  }

  async function send() {
    const typed = draft.trim();
    const text = typed || (pendingAttachments.length ? "Analyse les fichiers joints et réponds à partir de leur contenu." : "");
    if (!text || busy || uploadingAttachment) return;
    const attachmentsForMessage = [...pendingAttachments];
    setBusy(true); setError(""); setDraft("");
    const optimistic: AIMessage = { id: -Date.now(), role: "user", content: text, sources: [], attachments: attachmentsForMessage, created_at: new Date().toISOString() };
    setMessages((rows) => [...rows, optimistic]);
    try {
      const result = await api.post<ChatResult>("/ai/chat/", {
        conversation_id: activeId,
        message: text,
        response_style: style,
        page_context: pageContext,
        attachment_ids: attachmentsForMessage.map((row) => row.id),
      });
      setPendingAttachments([]);
      setActiveId(result.conversation_id);
      setMessages((rows) => [...rows.filter((m) => m.id !== optimistic.id), optimistic, result.message]);
      setStatus((current) => current ? { ...current, quota: result.quota } : current);
      if (status?.history_enabled !== false) {
        const list = await api.get<{ results?: AIConversation[] } | AIConversation[]>("/ai/conversations/?archived=false");
        setConversations(unwrap(list));
      }
    } catch (e) {
      setMessages((rows) => rows.filter((m) => m.id !== optimistic.id));
      setDraft(text);
      setError(e instanceof ApiError ? e.message : "L'assistant n'a pas pu répondre.");
    } finally { setBusy(false); }
  }

  if (!hydrated) return <div className="grid min-h-[240px] place-items-center text-sm text-slate-400"><Loader2 className="animate-spin" /></div>;
  if (!user) return <div className="grid min-h-[260px] place-items-center p-6 text-center"><div><Bot className="mx-auto text-brand-500" /><h2 className="mt-3 font-black">KalanPro AI</h2><p className="mt-2 text-sm text-slate-500">Connectez-vous pour utiliser votre assistant contextuel.</p><Link href="/login" className="btn-primary mt-5">Se connecter</Link></div></div>;
  if (status && !status.enabled) return <div className="grid min-h-[260px] place-items-center p-6 text-center text-sm text-slate-500">L'assistant IA n'est pas activé pour votre profil.</div>;

  return (
    <div className={`flex overflow-hidden bg-white ${embedded ? "h-[min(760px,calc(100vh-8rem))] rounded-3xl border border-slate-200 shadow-soft" : "h-full"}`}>
      {status?.history_enabled !== false && <aside className="hidden w-64 shrink-0 flex-col border-r border-slate-200 bg-slate-50/80 md:flex">
        <div className="border-b border-slate-200 p-3"><button onClick={newConversation} className="btn-primary w-full !py-2.5"><MessageSquarePlus size={16}/> Nouvelle conversation</button></div>
        <div className="min-h-0 flex-1 overflow-y-auto p-2">
          <p className="px-2 py-2 text-[11px] font-black uppercase tracking-[.12em] text-slate-400">Historique</p>
          {conversations.map((row) => <div key={row.id} className={`group flex items-center gap-1 rounded-xl ${activeId === row.id ? "bg-white shadow-sm" : "hover:bg-white"}`}>
            <button onClick={() => openConversation(row.id)} className="min-w-0 flex-1 px-3 py-2.5 text-left"><p className="truncate text-sm font-semibold text-navy-950">{row.title}</p><p className="mt-0.5 text-[10px] text-slate-400">{new Date(row.updated_at).toLocaleDateString("fr-FR")}</p></button>
            <button onClick={() => removeConversation(row.id)} className="mr-1 rounded-lg p-1.5 text-slate-300 opacity-0 hover:bg-red-50 hover:text-red-500 group-hover:opacity-100" aria-label="Supprimer"><Trash2 size={13}/></button>
          </div>)}
          {!conversations.length && <p className="px-3 py-5 text-xs text-slate-400">Vos conversations apparaîtront ici.</p>}
        </div>
      </aside>}

      <section className="flex min-w-0 flex-1 flex-col">
        <header className="flex min-h-[72px] items-center justify-between gap-3 border-b border-slate-200 px-4 py-3 pr-3">
          <div className="min-w-0 flex-1"><div className="flex items-center gap-2 font-black text-navy-950"><span className="grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-brand-500 to-orange-400 text-white"><Bot size={17}/></span><span className="truncate">KalanPro AI</span></div><p className="mt-0.5 truncate text-[10px] text-slate-400">{status?.dry_run ? "Mode démonstration" : status?.model || "Assistant contextuel"} · {status?.tools_enabled ? "Outils actifs" : "Lecture seule"} · {contextLabel(pageContext)}</p></div>
          <div className="flex shrink-0 items-center gap-1.5 sm:gap-2"><select value={style} onChange={(e) => setStyle(e.target.value as typeof style)} className="hidden rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs sm:block"><option value="short">Court</option><option value="normal">Normal</option><option value="detailed">Détaillé</option></select>{status?.quota && <span className="hidden rounded-lg bg-slate-100 px-2 py-1.5 text-[10px] font-bold text-slate-500 md:inline">{status.quota.unlimited ? "Illimité" : `${status.quota.remaining}/${status.quota.limit}`}</span>}{panelActions}</div>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto bg-[linear-gradient(180deg,#f8fafc_0%,#fff_50%)] p-4 sm:p-5">
          {loadingConversation ? <div className="grid h-full place-items-center"><Loader2 className="animate-spin text-brand-500" /></div> : !messages.length ? <Welcome userRole={user.role} capabilities={status?.capabilities || []} onPrompt={(value) => setDraft(value)} /> : <div className="mx-auto max-w-3xl space-y-5">{messages.map((message) => <MessageBubble key={message.id} message={message} />)}{busy && <div className="flex items-center gap-2 text-sm text-slate-400"><span className="grid h-8 w-8 place-items-center rounded-xl bg-brand-50 text-brand-600"><Bot size={16}/></span><Loader2 size={15} className="animate-spin"/> KalanPro AI analyse votre contexte…</div>}<div ref={endRef}/></div>}
        </div>

        <footer className="border-t border-slate-200 bg-white p-3 sm:p-4">
          {error && <div className="mb-2 rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-xs text-red-700">{error}</div>}
          {status && !status.dry_run && !status.provider_ready && <div className="mx-auto mb-2 max-w-3xl rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">{user.role === "admin" ? "Le fournisseur IA n’est pas encore configuré : renseignez la clé et le modèle côté serveur." : "KalanPro AI est temporairement indisponible pendant sa configuration."}</div>}
          <div className="mx-auto max-w-3xl">
            {pendingAttachments.length > 0 && <div className="mb-2 flex flex-wrap gap-2">{pendingAttachments.map((row) => <div key={row.id} className="flex max-w-full items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-2.5 py-2 text-xs text-slate-600"><span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-white text-brand-600">{row.is_image ? <ImageIcon size={14}/> : <FileText size={14}/>}</span><button type="button" onClick={() => void apiDownload(row.download_path.replace("/api", ""), row.name)} className="max-w-[180px] truncate font-semibold hover:text-brand-600" title={row.name}>{row.name}</button><span className="hidden text-[10px] text-slate-400 sm:inline">{Math.max(1, Math.round(row.size_bytes / 1024))} Ko</span><button type="button" onClick={() => void removePendingAttachment(row)} className="rounded-md p-1 text-slate-400 hover:bg-red-50 hover:text-red-500" aria-label={`Retirer ${row.name}`}><X size={12}/></button></div>)}</div>}
            {uploadingAttachment && <div className="mb-2 flex items-center gap-2 text-xs text-slate-500"><Loader2 size={13} className="animate-spin"/> Chargement du fichier… {uploadProgress > 0 ? `${uploadProgress}%` : ""}</div>}
            <div onDragOver={(e) => { if (status?.attachments_enabled) e.preventDefault(); }} onDrop={(e) => { if (!status?.attachments_enabled) return; e.preventDefault(); void uploadFiles(e.dataTransfer.files); }} className="flex items-end gap-2 rounded-2xl border border-slate-200 bg-white p-2 shadow-sm focus-within:border-brand-300 focus-within:ring-2 focus-within:ring-brand-100">
              {status?.attachments_enabled && <><input ref={fileInputRef} type="file" multiple accept=".pdf,.docx,.txt,.csv,.md,.json,.xlsx,.pptx,.png,.jpg,.jpeg,.webp" className="hidden" onChange={(e) => { if (e.target.files) void uploadFiles(e.target.files); }}/><button type="button" disabled={uploadingAttachment || pendingAttachments.length >= (status.max_attachments_per_message || 5)} onClick={() => fileInputRef.current?.click()} className="grid h-10 w-10 shrink-0 place-items-center rounded-xl text-slate-500 transition hover:bg-brand-50 hover:text-brand-600 disabled:opacity-40" aria-label="Joindre un fichier" title={`Joindre un fichier · ${status.max_attachment_mb || 12} Mo max`}><Paperclip size={17}/></button></>}
              <textarea value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void send(); } }} rows={2} maxLength={4000} placeholder="Posez une question ou joignez un CV, PDF, document…" className="min-h-[48px] flex-1 resize-none border-0 bg-transparent px-2 py-2 text-sm outline-none placeholder:text-slate-400" />
              <button disabled={(!draft.trim() && !pendingAttachments.length) || busy || uploadingAttachment || (!!status && !status.dry_run && !status.provider_ready) || (status?.quota && !status.quota.unlimited && status.quota.remaining <= 0)} onClick={() => void send()} className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-brand-500 text-white transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-40" aria-label="Envoyer"><Send size={17}/></button>
            </div>
            {status?.attachments_enabled && <p className="mt-1.5 text-center text-[10px] text-slate-400">PDF, Word, TXT, CSV, Markdown, JSON, Excel, PowerPoint et images · {status.max_attachment_mb || 12} Mo max/fichier{status.vision_enabled ? " · analyse visuelle activée" : " · images analysables si le modèle vision est activé"}</p>}
          </div>
          <p className="mx-auto mt-2 max-w-3xl text-center text-[10px] text-slate-400">L'IA peut se tromper. Les sources KalanPro utilisées sont affichées sous la réponse lorsqu'elles sont disponibles.</p>
        </footer>
      </section>
    </div>
  );
}

export default function KalanProAssistant({ initialOpen = false }: { initialOpen?: boolean }) {
  const pathname = usePathname();
  const { user, hydrated } = useAuth();
  const [open, setOpen] = useState(initialOpen);
  const [large, setLarge] = useState(false);
  const [launcherPosition, setLauncherPosition] = useState<{ x: number; y: number } | null>(null);
  const [draggingLauncher, setDraggingLauncher] = useState(false);
  const launcherRef = useRef<HTMLButtonElement | null>(null);
  const dragRef = useRef<{
    pointerId: number;
    startX: number;
    startY: number;
    originX: number;
    originY: number;
    moved: boolean;
  } | null>(null);
  const suppressLauncherClick = useRef(false);
  const launcherStorageKey = "kalanpro-ai-launcher-position-v1";

  function clampLauncherPosition(x: number, y: number) {
    if (typeof window === "undefined") return { x, y };
    const rect = launcherRef.current?.getBoundingClientRect();
    const width = rect?.width || 170;
    const height = rect?.height || 48;
    const margin = 12;
    return {
      x: Math.min(Math.max(margin, x), Math.max(margin, window.innerWidth - width - margin)),
      y: Math.min(Math.max(margin, y), Math.max(margin, window.innerHeight - height - margin)),
    };
  }

  function persistLauncherPosition(position: { x: number; y: number }) {
    try {
      window.localStorage.setItem(launcherStorageKey, JSON.stringify(position));
    } catch {
      // Une préférence d'interface ne doit jamais bloquer l'assistant.
    }
  }

  const firstPathEffect = useRef(true);
  useEffect(() => {
    // Quand le gros module IA vient d'être chargé après un clic sur le launcher léger,
    // conserver initialOpen=true au premier rendu. Les navigations suivantes ferment le panneau.
    if (firstPathEffect.current) {
      firstPathEffect.current = false;
      return;
    }
    setOpen(false);
    setLarge(false);
    window.requestAnimationFrame(() => {
      setLauncherPosition((current) => {
        if (!current) return current;
        const next = clampLauncherPosition(current.x, current.y);
        persistLauncherPosition(next);
        return next;
      });
    });
  }, [pathname]);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(launcherStorageKey);
      if (!raw) return;
      const parsed = JSON.parse(raw) as { x?: unknown; y?: unknown };
      if (typeof parsed.x !== "number" || typeof parsed.y !== "number") return;
      window.requestAnimationFrame(() => setLauncherPosition(clampLauncherPosition(parsed.x as number, parsed.y as number)));
    } catch {
      // Valeur locale absente ou invalide : conserver la position par défaut.
    }
  }, []);

  useEffect(() => {
    const onResize = () => {
      setLauncherPosition((current) => {
        if (!current) return current;
        const next = clampLauncherPosition(current.x, current.y);
        persistLauncherPosition(next);
        return next;
      });
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open]);

  function onLauncherPointerDown(event: ReactPointerEvent<HTMLButtonElement>) {
    if (event.button !== 0 && event.pointerType === "mouse") return;
    const rect = event.currentTarget.getBoundingClientRect();
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originX: rect.left,
      originY: rect.top,
      moved: false,
    };
    suppressLauncherClick.current = false;
    setDraggingLauncher(true);
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function onLauncherPointerMove(event: ReactPointerEvent<HTMLButtonElement>) {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    const dx = event.clientX - drag.startX;
    const dy = event.clientY - drag.startY;
    if (!drag.moved && Math.hypot(dx, dy) < 5) return;
    drag.moved = true;
    suppressLauncherClick.current = true;
    setLauncherPosition(clampLauncherPosition(drag.originX + dx, drag.originY + dy));
  }

  function finishLauncherDrag(event: ReactPointerEvent<HTMLButtonElement>) {
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) return;
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
    dragRef.current = null;
    setDraggingLauncher(false);
    if (drag.moved) {
      setLauncherPosition((current) => {
        if (current) persistLauncherPosition(current);
        return current;
      });
      window.setTimeout(() => { suppressLauncherClick.current = false; }, 0);
    }
  }

  function onLauncherClick() {
    if (suppressLauncherClick.current) return;
    setOpen(true);
  }

  if (!hydrated || pathname.startsWith("/live/session/") || pathname === "/assistant") return null;

  const controls = <>
    <button onClick={() => setLarge((v) => !v)} className="grid h-9 w-9 place-items-center rounded-xl border border-slate-200 bg-white text-slate-500 transition hover:border-brand-200 hover:bg-brand-50 hover:text-brand-600" aria-label={large ? "Réduire l'assistant" : "Agrandir l'assistant"} title={large ? "Réduire" : "Agrandir"}>{large ? <Minimize2 size={16}/> : <Maximize2 size={16}/>}</button>
    <button onClick={() => setOpen(false)} className="grid h-9 w-9 place-items-center rounded-xl border border-slate-200 bg-white text-slate-500 transition hover:border-red-200 hover:bg-red-50 hover:text-red-500" aria-label="Fermer KalanPro AI" title="Fermer"><X size={17}/></button>
  </>;

  const launcherStyle = launcherPosition
    ? { left: launcherPosition.x, top: launcherPosition.y, right: "auto", bottom: "auto" }
    : undefined;

  return <>
    {!open && <button
      ref={launcherRef}
      type="button"
      onClick={onLauncherClick}
      onPointerDown={onLauncherPointerDown}
      onPointerMove={onLauncherPointerMove}
      onPointerUp={finishLauncherDrag}
      onPointerCancel={finishLauncherDrag}
      style={{ ...launcherStyle, touchAction: "none" }}
      className={`fixed z-[70] flex select-none items-center gap-2 rounded-full bg-gradient-to-r from-brand-500 to-orange-400 px-4 py-3 text-sm font-black text-white shadow-[0_15px_45px_rgba(255,100,26,.35)] transition-shadow ${launcherPosition ? "" : "bottom-[max(5.5rem,env(safe-area-inset-bottom))] right-[max(1rem,env(safe-area-inset-right))] sm:right-[max(1.5rem,env(safe-area-inset-right))]"} ${draggingLauncher ? "cursor-grabbing shadow-[0_18px_55px_rgba(255,100,26,.45)]" : "cursor-grab hover:shadow-[0_18px_50px_rgba(255,100,26,.42)]"}`}
      aria-label="Ouvrir KalanPro AI. Glissez pour déplacer le bouton."
      title="KalanPro AI · Glissez pour déplacer"
    ><Sparkles size={17}/> <span className={pathname === "/" ? "inline" : "hidden sm:inline"}>{user ? "KalanPro AI" : "Essayer KalanPro AI"}</span></button>}
    {open && <div role="dialog" aria-modal="true" aria-label="KalanPro AI" className={`fixed z-[100] overflow-hidden border border-slate-200 bg-white shadow-2xl transition-all ${large ? "inset-2 rounded-2xl sm:inset-6 sm:rounded-3xl" : "bottom-[max(1rem,env(safe-area-inset-bottom))] right-[max(.75rem,env(safe-area-inset-right))] top-24 w-[calc(100%-1.5rem)] rounded-2xl sm:right-[max(1.5rem,env(safe-area-inset-right))] sm:w-[min(760px,calc(100%-3rem))] sm:rounded-3xl"}`}>
      <AssistantWorkspace panelActions={controls} />
    </div>}
  </>;
}

function Welcome({ userRole, capabilities, onPrompt }: { userRole: string; capabilities: string[]; onPrompt: (value: string) => void }) {
  let prompts: string[];
  if (userRole === "admin") prompts = ["Que peux-tu analyser dans KalanPro ?", "Analyse les contrôles qualité IA", "Montre-moi les outils disponibles"] ;
  else if (capabilities.includes("recruiter")) prompts = ["Montre-moi les candidatures reçues", "Prépare une scorecard pondérée pour un entretien", "Analyse une candidature et propose les prochaines étapes sans décision automatique"];
  else if (capabilities.includes("mentor")) prompts = ["Prépare ma prochaine séance de mentorat", "Montre-moi mes séances confirmées", "Crée un plan d’accompagnement et demande ma confirmation"];
  else if (userRole === "instructor") prompts = ["Crée un vrai cours brouillon sur mon domaine et demande ma confirmation", "Montre-moi mes contenus instructeur", "Crée 5 questions de quiz à partir du cours ouvert"];
  else prompts = ["Simule un entretien pour l’offre ouverte, une question à la fois", "Évalue ma préparation à l’entretien et propose un plan d’amélioration", "Prépare un message de suivi après mon entretien"];
  return <div className="mx-auto flex h-full max-w-2xl flex-col items-center justify-center py-10 text-center"><span className="grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-brand-500 to-orange-400 text-white shadow-lg"><Sparkles size={25}/></span><h2 className="mt-4 text-xl font-black text-navy-950">Que voulez-vous accomplir ?</h2><p className="mt-2 max-w-lg text-sm leading-6 text-slate-500">Je peux utiliser votre contexte KalanPro, vos contenus autorisés, vos outils métier et les fichiers que vous joignez.</p><div className="mt-6 grid w-full gap-2 sm:grid-cols-3">{prompts.map((prompt) => <button key={prompt} onClick={() => onPrompt(prompt)} className="rounded-2xl border border-slate-200 bg-white p-3 text-left text-xs font-semibold leading-5 text-slate-600 transition hover:border-brand-200 hover:bg-brand-50 hover:text-brand-700">{prompt}</button>)}</div></div>;
}

function MessageBubble({ message }: { message: AIMessage }) {
  const assistant = message.role === "assistant";
  const [feedback, setFeedback] = useState<"helpful" | "unhelpful" | "">(message.feedback || "");
  const [ratingBusy, setRatingBusy] = useState(false);
  const [actions, setActions] = useState<AIAction[]>(message.actions || []);
  const [messageAttachments, setMessageAttachments] = useState<AIAttachment[]>(message.attachments || []);
  const [actionBusy, setActionBusy] = useState<string | null>(null);


  async function removeHistoricAttachment(row: AIAttachment) {
    if (assistant || message.id <= 0) return;
    if (!confirm(`Supprimer définitivement « ${row.name} » de cette conversation ?`)) return;
    try {
      await api.del(`/ai/attachments/${row.id}/`);
      setMessageAttachments((current) => current.filter((item) => item.id !== row.id));
    } catch {
      // La conversation reste utilisable même si la suppression du fichier échoue.
    }
  }

  async function rate(next: "helpful" | "unhelpful") {
    if (!assistant || message.id <= 0 || ratingBusy) return;
    const desired = feedback === next ? "clear" : next;
    setRatingBusy(true);
    try {
      const result = await api.post<{ feedback: "helpful" | "unhelpful" | "" }>(`/ai/messages/${message.id}/feedback/`, { feedback: desired });
      setFeedback(result.feedback || "");
    } catch {
      // Le feedback ne doit jamais interrompre la conversation.
    } finally { setRatingBusy(false); }
  }

  async function decide(action: AIAction, decision: "confirm" | "reject") {
    if (!action.token || actionBusy) return;
    setActionBusy(action.token);
    try {
      const result = await api.post<{ action: AIAction }>(`/ai/actions/${action.token}/${decision}/`, {});
      setActions((rows) => rows.map((row) => row.token === action.token ? result.action : row));
    } catch (error) {
      const text = error instanceof ApiError ? error.message : "Action impossible.";
      setActions((rows) => rows.map((row) => row.token === action.token ? { ...row, error: text } : row));
    } finally { setActionBusy(null); }
  }

  return <div className={`flex gap-3 ${assistant ? "" : "justify-end"}`}>
    {assistant && <span className="grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-brand-50 text-brand-600"><Bot size={16}/></span>}
    <div className={`max-w-[88%] ${assistant ? "" : "rounded-2xl rounded-tr-md bg-navy-950 px-4 py-3 text-white"}`}>
      <div className={`whitespace-pre-wrap text-sm leading-6 ${assistant ? "text-slate-700" : "text-white"}`}>{message.content}</div>
      {messageAttachments.length > 0 && <div className="mt-2 flex flex-wrap gap-2">{messageAttachments.map((row) => <div key={row.id} className={`inline-flex max-w-full items-center gap-1 rounded-lg border px-2 py-1 text-[10px] font-semibold ${assistant ? "border-slate-200 bg-white text-slate-500" : "border-white/20 bg-white/10 text-white"}`}><button type="button" onClick={() => void apiDownload(row.download_path.replace("/api", ""), row.name)} className={`inline-flex min-w-0 items-center gap-1.5 ${assistant ? "hover:text-brand-600" : "hover:text-white/80"}`} title={row.name}>{row.is_image ? <ImageIcon size={11}/> : <FileText size={11}/>}<span className="max-w-[180px] truncate">{row.name}</span></button>{!assistant && message.id > 0 && <button type="button" onClick={() => void removeHistoricAttachment(row)} className="rounded p-0.5 text-white/60 hover:bg-white/10 hover:text-white" aria-label={`Supprimer ${row.name}`}><X size={10}/></button>}</div>)}</div>}
      {assistant && message.sources?.length > 0 && <div className="mt-3 flex flex-wrap gap-2">{message.sources.slice(0, 6).map((source) => <Link key={source.id} href={source.path || "#"} title={source.score ? `Pertinence RAG : ${source.score.toFixed(1)}` : undefined} className="inline-flex max-w-full items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1 text-[10px] font-semibold text-slate-500 hover:border-brand-200 hover:text-brand-600"><span className="truncate">{source.title}</span><ExternalLink size={10}/></Link>)}</div>}
      {assistant && actions.length > 0 && <div className="mt-3 space-y-2">{actions.map((action) => <ActionCard key={action.token || action.id} action={action} busy={actionBusy === action.token} onConfirm={() => void decide(action, "confirm")} onReject={() => void decide(action, "reject")} />)}</div>}
      {assistant && <div className="mt-2 flex items-center gap-1 text-slate-400"><span className="mr-1 text-[10px]">Cette réponse vous aide ?</span><button type="button" disabled={ratingBusy} onClick={() => void rate("helpful")} className={`rounded-lg p-1.5 transition ${feedback === "helpful" ? "bg-emerald-50 text-emerald-600" : "hover:bg-slate-100 hover:text-slate-600"}`} aria-label="Réponse utile"><ThumbsUp size={13}/></button><button type="button" disabled={ratingBusy} onClick={() => void rate("unhelpful")} className={`rounded-lg p-1.5 transition ${feedback === "unhelpful" ? "bg-red-50 text-red-500" : "hover:bg-slate-100 hover:text-slate-600"}`} aria-label="Réponse à améliorer"><ThumbsDown size={13}/></button></div>}
    </div>
  </div>;
}

function ActionCard({ action, busy, onConfirm, onReject }: { action: AIAction; busy: boolean; onConfirm: () => void; onReject: () => void }) {
  const proposed = action.status === "proposed";
  const executed = action.status === "executed";
  const rejected = action.status === "rejected";
  const failed = action.status === "failed";
  return <div className={`rounded-2xl border p-3 ${executed ? "border-emerald-200 bg-emerald-50/60" : rejected || failed ? "border-slate-200 bg-slate-50" : "border-brand-200 bg-brand-50/50"}`}>
    <div className="flex items-start gap-2">
      <span className={`mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-lg ${executed ? "bg-emerald-100 text-emerald-700" : proposed ? "bg-white text-brand-600" : "bg-white text-slate-500"}`}>{executed ? <Check size={14}/> : failed ? <Ban size={14}/> : <Wrench size={14}/>}</span>
      <div className="min-w-0 flex-1"><p className="text-xs font-black text-navy-950">{action.label}</p><p className="mt-0.5 text-[10px] text-slate-500">{executed ? "Action exécutée" : rejected ? "Action refusée" : failed ? "Action échouée" : "Votre confirmation est requise avant toute modification."}</p>{action.error && <p className="mt-1 text-[10px] text-red-600">{action.error}</p>}</div>
      {proposed && <ShieldCheck size={15} className="shrink-0 text-brand-500"/>}
    </div>
    {executed && typeof action.result?.path === "string" && <div className="mt-3"><Link href={action.result.path} className="inline-flex items-center gap-1 rounded-xl border border-emerald-200 bg-white px-3 py-2 text-[11px] font-black text-emerald-700 hover:bg-emerald-50">Ouvrir le résultat <ExternalLink size={11}/></Link></div>}
    {proposed && <div className="mt-3 flex flex-wrap gap-2"><button type="button" disabled={busy} onClick={onConfirm} className="inline-flex items-center gap-1 rounded-xl bg-brand-500 px-3 py-2 text-[11px] font-black text-white hover:bg-brand-600 disabled:opacity-50">{busy ? <Loader2 size={12} className="animate-spin"/> : <Check size={12}/>} Confirmer</button><button type="button" disabled={busy} onClick={onReject} className="inline-flex items-center gap-1 rounded-xl border border-slate-200 bg-white px-3 py-2 text-[11px] font-bold text-slate-600 hover:bg-slate-50 disabled:opacity-50"><X size={12}/> Refuser</button></div>}
  </div>;
}

function contextLabel(context: AIPageContext) {
  if (context.lesson_title) return `Leçon : ${context.lesson_title}`;
  if (context.course_slug) return "Cours actuel";
  if (context.pdf_slug) return "PDF actuel";
  if (context.opportunity_slug) return "Offre actuelle";
  return "Contexte de la page";
}
