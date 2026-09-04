"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import {
  Bot, ChevronLeft, ExternalLink, History, Loader2, Maximize2, MessageSquarePlus,
  Minimize2, Send, Sparkles, Trash2, X, ThumbsUp, ThumbsDown,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { AI_CONTEXT_EVENT, AIPageContext, currentAIContext, inferAIContext } from "@/lib/aiContext";
import { useAuth } from "@/hooks/useAuth";
import type { AIConversation, AIMessage, AIQuota, AIStatus } from "@/types";

type Props = { embedded?: boolean };
type ChatResult = { conversation_id: number; message: AIMessage; quota: AIQuota; context: Record<string, unknown> };

function unwrap<T>(value: { results?: T[] } | T[]): T[] {
  return Array.isArray(value) ? value : value.results || [];
}

export function AssistantWorkspace({ embedded = false }: Props) {
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
  const [pageContext, setPageContext] = useState<AIPageContext>(() => currentAIContext(pathname));
  const endRef = useRef<HTMLDivElement | null>(null);

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

  async function openConversation(id: number) {
    setLoadingConversation(true); setError("");
    try {
      const value = await api.get<AIConversation>(`/ai/conversations/${id}/`);
      setActiveId(id); setMessages(value.messages || []);
    } catch (e) { setError(e instanceof ApiError ? e.message : "Conversation indisponible."); }
    finally { setLoadingConversation(false); }
  }

  function newConversation() { setActiveId(null); setMessages([]); setDraft(""); setError(""); }

  async function removeConversation(id: number) {
    if (!confirm("Supprimer cette conversation IA ?")) return;
    try {
      await api.del(`/ai/conversations/${id}/`);
      setConversations((rows) => rows.filter((row) => row.id !== id));
      if (activeId === id) newConversation();
    } catch (e) { setError(e instanceof ApiError ? e.message : "Suppression impossible."); }
  }

  async function send() {
    const text = draft.trim();
    if (!text || busy) return;
    setBusy(true); setError(""); setDraft("");
    const optimistic: AIMessage = { id: -Date.now(), role: "user", content: text, sources: [], created_at: new Date().toISOString() };
    setMessages((rows) => [...rows, optimistic]);
    try {
      const result = await api.post<ChatResult>("/ai/chat/", {
        conversation_id: activeId,
        message: text,
        response_style: style,
        page_context: pageContext,
      });
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
        <header className="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-3">
          <div className="min-w-0"><div className="flex items-center gap-2 font-black text-navy-950"><span className="grid h-8 w-8 place-items-center rounded-xl bg-gradient-to-br from-brand-500 to-orange-400 text-white"><Bot size={17}/></span>KalanPro AI</div><p className="mt-0.5 truncate text-[10px] text-slate-400">{status?.dry_run ? "Mode démonstration" : status?.model || "Assistant contextuel"} · {contextLabel(pageContext)}</p></div>
          <div className="flex items-center gap-2"><select value={style} onChange={(e) => setStyle(e.target.value as typeof style)} className="rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs"><option value="short">Court</option><option value="normal">Normal</option><option value="detailed">Détaillé</option></select>{status?.quota && <span className="hidden rounded-lg bg-slate-100 px-2 py-1.5 text-[10px] font-bold text-slate-500 sm:inline">{status.quota.unlimited ? "Illimité" : `${status.quota.remaining}/${status.quota.limit}`}</span>}</div>
        </header>

        <div className="min-h-0 flex-1 overflow-y-auto bg-[linear-gradient(180deg,#f8fafc_0%,#fff_50%)] p-4 sm:p-5">
          {loadingConversation ? <div className="grid h-full place-items-center"><Loader2 className="animate-spin text-brand-500" /></div> : !messages.length ? <Welcome userRole={user.role} onPrompt={(value) => setDraft(value)} /> : <div className="mx-auto max-w-3xl space-y-5">{messages.map((message) => <MessageBubble key={message.id} message={message} />)}{busy && <div className="flex items-center gap-2 text-sm text-slate-400"><span className="grid h-8 w-8 place-items-center rounded-xl bg-brand-50 text-brand-600"><Bot size={16}/></span><Loader2 size={15} className="animate-spin"/> KalanPro AI analyse votre contexte…</div>}<div ref={endRef}/></div>}
        </div>

        <footer className="border-t border-slate-200 bg-white p-3 sm:p-4">
          {error && <div className="mb-2 rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-xs text-red-700">{error}</div>}
          {status && !status.dry_run && !status.provider_ready && <div className="mx-auto mb-2 max-w-3xl rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800">{user.role === "admin" ? "Le fournisseur IA n’est pas encore configuré : renseignez la clé et le modèle côté serveur." : "KalanPro AI est temporairement indisponible pendant sa configuration."}</div>}
          <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-2xl border border-slate-200 bg-white p-2 shadow-sm focus-within:border-brand-300 focus-within:ring-2 focus-within:ring-brand-100">
            <textarea value={draft} onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void send(); } }} rows={2} maxLength={4000} placeholder="Posez une question sur votre cours, votre progression ou votre contenu…" className="min-h-[48px] flex-1 resize-none border-0 bg-transparent px-2 py-2 text-sm outline-none placeholder:text-slate-400" />
            <button disabled={!draft.trim() || busy || (!!status && !status.dry_run && !status.provider_ready) || (status?.quota && !status.quota.unlimited && status.quota.remaining <= 0)} onClick={() => void send()} className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-brand-500 text-white transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:opacity-40" aria-label="Envoyer"><Send size={17}/></button>
          </div>
          <p className="mx-auto mt-2 max-w-3xl text-center text-[10px] text-slate-400">L'IA peut se tromper. Les sources KalanPro utilisées sont affichées sous la réponse lorsqu'elles sont disponibles.</p>
        </footer>
      </section>
    </div>
  );
}

export default function KalanProAssistant() {
  const pathname = usePathname();
  const { user, hydrated } = useAuth();
  const [open, setOpen] = useState(false);
  const [large, setLarge] = useState(false);
  if (!hydrated || !user || pathname.startsWith("/live/session/") || pathname === "/assistant") return null;
  return <>
    <button onClick={() => setOpen(true)} className="fixed bottom-5 right-4 z-40 flex items-center gap-2 rounded-full bg-gradient-to-r from-brand-500 to-orange-400 px-4 py-3 text-sm font-black text-white shadow-[0_15px_45px_rgba(255,100,26,.35)] transition hover:-translate-y-0.5 sm:right-6" aria-label="Ouvrir KalanPro AI"><Sparkles size={17}/> <span className="hidden sm:inline">KalanPro AI</span></button>
    {open && <div className={`fixed z-[80] overflow-hidden border border-slate-200 bg-white shadow-2xl transition-all ${large ? "inset-3 rounded-3xl sm:inset-6" : "bottom-4 right-3 top-24 w-[calc(100%-1.5rem)] rounded-3xl sm:right-6 sm:w-[min(760px,calc(100%-3rem))]"}`}>
      <div className="absolute right-3 top-3 z-20 flex gap-1"><button onClick={() => setLarge((v) => !v)} className="rounded-lg bg-white/90 p-2 text-slate-500 shadow-sm hover:bg-slate-100" aria-label={large ? "Réduire" : "Agrandir"}>{large ? <Minimize2 size={15}/> : <Maximize2 size={15}/>}</button><button onClick={() => setOpen(false)} className="rounded-lg bg-white/90 p-2 text-slate-500 shadow-sm hover:bg-slate-100" aria-label="Fermer"><X size={16}/></button></div>
      <AssistantWorkspace />
    </div>}
  </>;
}

function Welcome({ userRole, onPrompt }: { userRole: string; onPrompt: (value: string) => void }) {
  const prompts = userRole === "instructor" ? ["Crée 5 questions de quiz à partir du cours ouvert", "Aide-moi à améliorer les objectifs pédagogiques", "Résume les points clés de cette leçon"] : userRole === "admin" ? ["Que peux-tu analyser dans KalanPro ?", "Explique le fonctionnement du RAG KalanPro", "Quels contrôles qualité recommandes-tu ?"] : ["Explique-moi la leçon actuelle simplement", "Fais-moi un mini quiz de 5 questions", "Résume ce cours en points clés"];
  return <div className="mx-auto flex h-full max-w-2xl flex-col items-center justify-center py-10 text-center"><span className="grid h-14 w-14 place-items-center rounded-2xl bg-gradient-to-br from-brand-500 to-orange-400 text-white shadow-lg"><Sparkles size={25}/></span><h2 className="mt-4 text-xl font-black text-navy-950">Que voulez-vous accomplir ?</h2><p className="mt-2 max-w-lg text-sm leading-6 text-slate-500">Je peux utiliser votre contexte KalanPro, les cours auxquels vous avez accès, les transcriptions et les PDF indexés.</p><div className="mt-6 grid w-full gap-2 sm:grid-cols-3">{prompts.map((prompt) => <button key={prompt} onClick={() => onPrompt(prompt)} className="rounded-2xl border border-slate-200 bg-white p-3 text-left text-xs font-semibold leading-5 text-slate-600 transition hover:border-brand-200 hover:bg-brand-50 hover:text-brand-700">{prompt}</button>)}</div></div>;
}

function MessageBubble({ message }: { message: AIMessage }) {
  const assistant = message.role === "assistant";
  const [feedback, setFeedback] = useState<"helpful" | "unhelpful" | "">(message.feedback || "");
  const [ratingBusy, setRatingBusy] = useState(false);

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

  return <div className={`flex gap-3 ${assistant ? "" : "justify-end"}`}>{assistant && <span className="grid h-8 w-8 shrink-0 place-items-center rounded-xl bg-brand-50 text-brand-600"><Bot size={16}/></span>}<div className={`max-w-[88%] ${assistant ? "" : "rounded-2xl rounded-tr-md bg-navy-950 px-4 py-3 text-white"}`}><div className={`whitespace-pre-wrap text-sm leading-6 ${assistant ? "text-slate-700" : "text-white"}`}>{message.content}</div>{assistant && message.sources?.length > 0 && <div className="mt-3 flex flex-wrap gap-2">{message.sources.slice(0, 6).map((source) => <Link key={source.id} href={source.path || "#"} title={source.score ? `Pertinence RAG : ${source.score.toFixed(1)}` : undefined} className="inline-flex max-w-full items-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1 text-[10px] font-semibold text-slate-500 hover:border-brand-200 hover:text-brand-600"><span className="truncate">{source.title}</span><ExternalLink size={10}/></Link>)}</div>}{assistant && <div className="mt-2 flex items-center gap-1 text-slate-400"><span className="mr-1 text-[10px]">Cette réponse vous aide ?</span><button type="button" disabled={ratingBusy} onClick={() => void rate("helpful")} className={`rounded-lg p-1.5 transition ${feedback === "helpful" ? "bg-emerald-50 text-emerald-600" : "hover:bg-slate-100 hover:text-slate-600"}`} aria-label="Réponse utile"><ThumbsUp size={13}/></button><button type="button" disabled={ratingBusy} onClick={() => void rate("unhelpful")} className={`rounded-lg p-1.5 transition ${feedback === "unhelpful" ? "bg-red-50 text-red-500" : "hover:bg-slate-100 hover:text-slate-600"}`} aria-label="Réponse à améliorer"><ThumbsDown size={13}/></button></div>}</div></div>;
}

function contextLabel(context: AIPageContext) {
  if (context.lesson_title) return `Leçon : ${context.lesson_title}`;
  if (context.course_slug) return "Cours actuel";
  if (context.pdf_slug) return "PDF actuel";
  return "Contexte de la page";
}
