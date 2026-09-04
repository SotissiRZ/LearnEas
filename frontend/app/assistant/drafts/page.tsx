"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Bot, ChevronLeft, ClipboardList, FileQuestion, Layers3, Loader2, Users } from "lucide-react";
import GuardScreen from "@/components/ui/GuardScreen";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import { api, ApiError } from "@/lib/api";

type DraftKind = "quiz" | "course_outline" | "mentor_plan" | "interview_rubric";
type AIDraft = {
  id: number;
  kind: DraftKind;
  title: string;
  payload: Record<string, unknown>;
  course_id: number | null;
  course_title: string;
  created_at: string;
  updated_at: string;
};

const meta: Record<DraftKind, { label: string; className: string }> = {
  quiz: { label: "Quiz", className: "bg-brand-50 text-brand-600" },
  course_outline: { label: "Plan de cours", className: "bg-blue-50 text-blue-600" },
  mentor_plan: { label: "Plan de mentorat", className: "bg-emerald-50 text-emerald-600" },
  interview_rubric: { label: "Grille d’entretien", className: "bg-violet-50 text-violet-600" },
};

export default function AssistantDraftsPage() {
  const { ready } = useAuthGuard();
  const [rows, setRows] = useState<AIDraft[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!ready) return;
    api.get<AIDraft[]>("/ai/drafts/")
      .then(setRows)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Brouillons indisponibles."))
      .finally(() => setLoading(false));
  }, [ready]);

  if (!ready) return <GuardScreen />;
  return <div className="container-app py-8">
    <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div><p className="text-xs font-black uppercase tracking-[.14em] text-brand-600">KalanPro AI · Phase 2</p><h1 className="mt-1 text-3xl font-black text-navy-950">Mes brouillons IA</h1><p className="mt-2 text-sm text-slate-500">Contenus pédagogiques, plans de mentorat et grilles d’entretien enregistrés uniquement après confirmation.</p></div>
      <Link href="/assistant" className="inline-flex items-center gap-2 text-sm font-bold text-brand-600 hover:text-brand-700"><ChevronLeft size={16}/> Retour à l’assistant</Link>
    </div>
    {error && <div className="mb-4 rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-700">{error}</div>}
    {loading ? <div className="grid min-h-48 place-items-center"><Loader2 className="animate-spin text-brand-500"/></div> : !rows.length ? <div className="card p-8 text-center"><Bot className="mx-auto text-brand-500"/><h2 className="mt-3 font-black text-navy-950">Aucun brouillon IA</h2><p className="mt-2 text-sm text-slate-500">Demandez à KalanPro AI de préparer un contenu, puis confirmez son enregistrement.</p></div> : <div className="grid gap-4 lg:grid-cols-2">{rows.map((row) => <DraftCard key={row.id} row={row}/>)}</div>}
  </div>;
}

function DraftIcon({ kind }: { kind: DraftKind }) {
  if (kind === "quiz") return <FileQuestion size={18}/>;
  if (kind === "course_outline") return <Layers3 size={18}/>;
  if (kind === "mentor_plan") return <Users size={18}/>;
  return <ClipboardList size={18}/>;
}

function DraftCard({ row }: { row: AIDraft }) {
  const info = meta[row.kind] || meta.course_outline;
  const questions = Array.isArray(row.payload.questions) ? row.payload.questions : [];
  const sections = Array.isArray(row.payload.sections) ? row.payload.sections : [];
  const agenda = Array.isArray(row.payload.agenda) ? row.payload.agenda : [];
  const criteria = Array.isArray(row.payload.criteria) ? row.payload.criteria : [];
  const summary = row.kind === "quiz" ? `${questions.length} question${questions.length > 1 ? "s" : ""}`
    : row.kind === "course_outline" ? `${sections.length} section${sections.length > 1 ? "s" : ""}`
    : row.kind === "mentor_plan" ? `${agenda.length} point${agenda.length > 1 ? "s" : ""} d’agenda`
    : `${criteria.length} critère${criteria.length > 1 ? "s" : ""} d’entretien`;
  return <article className="card p-5">
    <div className="flex items-start gap-3"><span className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ${info.className}`}><DraftIcon kind={row.kind}/></span><div className="min-w-0"><p className="text-[10px] font-black uppercase tracking-[.12em] text-slate-400">{info.label}</p><h2 className="truncate font-black text-navy-950">{row.title}</h2>{row.course_title && <p className="mt-1 text-xs text-slate-500">Cours : {row.course_title}</p>}</div></div>
    <div className="mt-4 rounded-xl bg-slate-50 p-3 text-sm text-slate-600">{summary}</div>
    {typeof row.payload.candidate === "string" && <p className="mt-3 text-xs text-slate-500">Candidat : {row.payload.candidate}</p>}
    {typeof row.payload.learner === "string" && <p className="mt-3 text-xs text-slate-500">Mentoré : {row.payload.learner}</p>}
    <p className="mt-3 text-[10px] text-slate-400">Mis à jour le {new Date(row.updated_at).toLocaleString("fr-FR")}</p>
  </article>;
}
