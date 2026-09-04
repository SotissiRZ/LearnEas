"use client";
import Link from "next/link";
import { AssistantWorkspace } from "@/components/ai/KalanProAssistant";
import GuardScreen from "@/components/ui/GuardScreen";
import { useAuthGuard } from "@/hooks/useAuthGuard";

export default function AssistantPage() {
  const { ready } = useAuthGuard();
  if (!ready) return <GuardScreen />;
  return <div className="container-app py-8"><div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between"><div><p className="text-xs font-black uppercase tracking-[.14em] text-brand-600">Copilote contextuel</p><h1 className="mt-1 text-3xl font-black text-navy-950">KalanPro AI</h1><p className="mt-2 text-sm text-slate-500">RAG, recherche structurée et actions KalanPro avec confirmation explicite.</p></div><Link href="/assistant/drafts" className="rounded-xl border border-slate-200 bg-white px-4 py-2 text-sm font-bold text-navy-950 hover:border-brand-200 hover:text-brand-600">Mes brouillons IA</Link></div><AssistantWorkspace embedded /></div>;
}
