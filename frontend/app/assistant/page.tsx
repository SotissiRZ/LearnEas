"use client";
import { AssistantWorkspace } from "@/components/ai/KalanProAssistant";
import GuardScreen from "@/components/ui/GuardScreen";
import { useAuthGuard } from "@/hooks/useAuthGuard";

export default function AssistantPage() {
  const { ready } = useAuthGuard();
  if (!ready) return <GuardScreen />;
  return <div className="container-app py-8"><div className="mb-5"><p className="text-xs font-black uppercase tracking-[.14em] text-brand-600">Copilote contextuel</p><h1 className="mt-1 text-3xl font-black text-navy-950">KalanPro AI</h1><p className="mt-2 text-sm text-slate-500">Retrouvez votre historique et interrogez vos contenus KalanPro depuis un espace dédié.</p></div><AssistantWorkspace embedded /></div>;
}
