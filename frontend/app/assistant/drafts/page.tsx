"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Bot, BriefcaseBusiness, ChevronLeft, ClipboardList, Download, FilePenLine, FileQuestion, GraduationCap, Layers3, Loader2, ScrollText, Users } from "lucide-react";
import GuardScreen from "@/components/ui/GuardScreen";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import { api, ApiError, apiDownload } from "@/lib/api";

type DraftKind = "quiz" | "course_outline" | "mentor_plan" | "interview_rubric" | "cv_improvement" | "cover_letter" | "learning_gap_plan" | "interview_prep" | "interview_score" | "interview_followup" | "recruiter_scorecard";
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
  interview_rubric: { label: "Grille d’entretien recruteur", className: "bg-violet-50 text-violet-600" },
  cv_improvement: { label: "CV amélioré", className: "bg-cyan-50 text-cyan-700" },
  cover_letter: { label: "Lettre de motivation", className: "bg-amber-50 text-amber-700" },
  learning_gap_plan: { label: "Plan de compétences", className: "bg-indigo-50 text-indigo-700" },
  interview_prep: { label: "Préparation entretien", className: "bg-rose-50 text-rose-700" },
  interview_score: { label: "Score de préparation", className: "bg-emerald-50 text-emerald-700" },
  interview_followup: { label: "Suivi post-entretien", className: "bg-orange-50 text-orange-700" },
  recruiter_scorecard: { label: "Scorecard recruteur", className: "bg-purple-50 text-purple-700" },
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
  if (kind === "cv_improvement") return <FilePenLine size={18}/>;
  if (kind === "cover_letter") return <ScrollText size={18}/>;
  if (kind === "learning_gap_plan") return <GraduationCap size={18}/>;
  if (kind === "interview_prep" || kind === "interview_score" || kind === "interview_followup") return <BriefcaseBusiness size={18}/>;
  return <ClipboardList size={18}/>;
}

function DraftCard({ row }: { row: AIDraft }) {
  const info = meta[row.kind] || meta.course_outline;
  const questions = Array.isArray(row.payload.questions) ? row.payload.questions : [];
  const sections = Array.isArray(row.payload.sections) ? row.payload.sections : [];
  const agenda = Array.isArray(row.payload.agenda) ? row.payload.agenda : [];
  const criteria = Array.isArray(row.payload.criteria) ? row.payload.criteria : [];
  const missingSkills = Array.isArray(row.payload.missing_skills) ? row.payload.missing_skills : [];
  const actions = Array.isArray(row.payload.actions) ? row.payload.actions : [];
  const likelyQuestions = Array.isArray(row.payload.likely_questions) ? row.payload.likely_questions : [];
  const skills = Array.isArray(row.payload.skills) ? row.payload.skills : [];
  const summary = row.kind === "quiz" ? `${questions.length} question${questions.length > 1 ? "s" : ""}`
    : row.kind === "course_outline" ? `${sections.length} section${sections.length > 1 ? "s" : ""}`
    : row.kind === "mentor_plan" ? `${agenda.length} point${agenda.length > 1 ? "s" : ""} d’agenda`
    : row.kind === "interview_rubric" ? `${criteria.length} critère${criteria.length > 1 ? "s" : ""} d’entretien`
    : row.kind === "cv_improvement" ? `${skills.length} compétence${skills.length > 1 ? "s" : ""} mise${skills.length > 1 ? "s" : ""} en avant`
    : row.kind === "cover_letter" ? "Lettre ciblée prête à relire"
    : row.kind === "learning_gap_plan" ? `${missingSkills.length} compétence${missingSkills.length > 1 ? "s" : ""} · ${actions.length} étape${actions.length > 1 ? "s" : ""}`
    : row.kind === "interview_score" ? `Préparation : ${Number(row.payload.overall_score || 0)}/100`
    : row.kind === "interview_followup" ? "Message de suivi prêt à relire"
    : row.kind === "recruiter_scorecard" ? `Score structuré : ${Number(row.payload.overall_score || 0)}/100`
    : `${likelyQuestions.length} question${likelyQuestions.length > 1 ? "s" : ""} probable${likelyQuestions.length > 1 ? "s" : ""}`;
  return <article className="card p-5">
    <div className="flex items-start gap-3"><span className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ${info.className}`}><DraftIcon kind={row.kind}/></span><div className="min-w-0"><p className="text-[10px] font-black uppercase tracking-[.12em] text-slate-400">{info.label}</p><h2 className="truncate font-black text-navy-950">{row.title}</h2>{row.course_title && <p className="mt-1 text-xs text-slate-500">Cours : {row.course_title}</p>}</div></div>
    <div className="mt-4 rounded-xl bg-slate-50 p-3 text-sm text-slate-600">{summary}</div>
    {typeof row.payload.candidate === "string" && <p className="mt-3 text-xs text-slate-500">Candidat : {row.payload.candidate}</p>}
    {typeof row.payload.learner === "string" && <p className="mt-3 text-xs text-slate-500">Mentoré : {row.payload.learner}</p>}
    {typeof row.payload.opportunity === "string" && row.payload.opportunity && <p className="mt-3 text-xs text-slate-500">Offre : {row.payload.opportunity}</p>}
    {typeof row.payload.professional_headline === "string" && row.payload.professional_headline && <p className="mt-3 line-clamp-2 text-xs font-semibold text-navy-950">{row.payload.professional_headline}</p>}
    {row.kind === "cover_letter" && typeof row.payload.content === "string" && <details className="mt-3 rounded-xl border border-slate-100 bg-white p-3"><summary className="cursor-pointer text-xs font-bold text-brand-600">Voir la lettre</summary><p className="mt-3 whitespace-pre-wrap text-xs leading-5 text-slate-600">{row.payload.content}</p></details>}
    {row.kind === "cv_improvement" && typeof row.payload.summary === "string" && <details className="mt-3 rounded-xl border border-slate-100 bg-white p-3"><summary className="cursor-pointer text-xs font-bold text-brand-600">Voir les améliorations CV</summary><p className="mt-3 whitespace-pre-wrap text-xs leading-5 text-slate-600">{row.payload.summary}</p>{Array.isArray(row.payload.recommendations) && row.payload.recommendations.length > 0 && <ul className="mt-3 list-disc space-y-1 pl-4 text-xs text-slate-600">{row.payload.recommendations.slice(0, 10).map((item, index) => <li key={index}>{String(item)}</li>)}</ul>}</details>}
    {row.kind === "learning_gap_plan" && actions.length > 0 && <details className="mt-3 rounded-xl border border-slate-100 bg-white p-3"><summary className="cursor-pointer text-xs font-bold text-brand-600">Voir le plan</summary><div className="mt-3 space-y-2">{actions.slice(0, 12).map((item, index) => { const value = item && typeof item === "object" ? item as Record<string, unknown> : {}; return <div key={index} className="rounded-lg bg-slate-50 p-2 text-xs text-slate-600"><span className="font-bold text-navy-950">{String(value.skill || "Compétence")}</span> · {String(value.action || "")}</div>; })}</div></details>}
    {row.kind === "interview_prep" && <details className="mt-3 rounded-xl border border-slate-100 bg-white p-3"><summary className="cursor-pointer text-xs font-bold text-brand-600">Voir la préparation</summary>{typeof row.payload.pitch === "string" && <p className="mt-3 whitespace-pre-wrap text-xs leading-5 text-slate-600">{row.payload.pitch}</p>}{likelyQuestions.length > 0 && <div className="mt-3"><p className="text-[10px] font-black uppercase tracking-[.1em] text-slate-400">Questions probables</p><ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-slate-600">{likelyQuestions.slice(0, 12).map((item, index) => <li key={index}>{String(item)}</li>)}</ul></div>}</details>}
    {row.kind === "interview_score" && <details className="mt-3 rounded-xl border border-slate-100 bg-white p-3"><summary className="cursor-pointer text-xs font-bold text-brand-600">Voir l’évaluation</summary><div className="mt-3 grid gap-2 sm:grid-cols-2">{row.payload.scores !== null && typeof row.payload.scores === "object" && Object.entries(row.payload.scores as Record<string, unknown>).map(([label,value]) => <div key={label} className="rounded-lg bg-slate-50 p-2 text-xs"><span className="font-semibold text-navy-950">{label}</span><span className="float-right font-black text-brand-600">{Number(value)}/100</span></div>)}</div>{typeof row.payload.response_summary === "string" && row.payload.response_summary && <p className="mt-3 whitespace-pre-wrap text-xs leading-5 text-slate-600">{row.payload.response_summary}</p>}</details>}
    {row.kind === "interview_followup" && <details className="mt-3 rounded-xl border border-slate-100 bg-white p-3"><summary className="cursor-pointer text-xs font-bold text-brand-600">Voir le suivi</summary>{typeof row.payload.subject === "string" && row.payload.subject && <p className="mt-3 text-xs font-bold text-navy-950">Objet : {row.payload.subject}</p>}{typeof row.payload.message === "string" && <p className="mt-3 whitespace-pre-wrap text-xs leading-5 text-slate-600">{row.payload.message}</p>}{typeof row.payload.recommended_send_window === "string" && row.payload.recommended_send_window && <p className="mt-3 text-[11px] text-slate-500">Moment recommandé : {row.payload.recommended_send_window}</p>}</details>}
    {row.kind === "recruiter_scorecard" && <details className="mt-3 rounded-xl border border-slate-100 bg-white p-3"><summary className="cursor-pointer text-xs font-bold text-brand-600">Voir la scorecard</summary><div className="mt-3 space-y-2">{Array.isArray(row.payload.criteria) && row.payload.criteria.slice(0, 15).map((raw,index) => { const item = raw && typeof raw === "object" ? raw as Record<string, unknown> : {}; return <div key={index} className="rounded-lg bg-slate-50 p-2 text-xs text-slate-600"><div className="flex items-center justify-between gap-3"><span className="font-bold text-navy-950">{String(item.name || "Critère")}</span><span className="font-black text-brand-600">{Number(item.score || 0)}/100</span></div><p className="mt-1 text-[11px] text-slate-500">Poids {Number(item.weight || 0)}%</p>{item.evidence ? <p className="mt-1">{String(item.evidence)}</p> : null}</div>; })}</div></details>}
    <div className="mt-4 flex flex-wrap items-center gap-2"><button type="button" onClick={() => void apiDownload(`/ai/drafts/${row.id}/export/?format=pdf`, `kalanpro-${row.id}.pdf`)} className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-bold text-slate-600 hover:border-brand-200 hover:text-brand-600"><Download size={13}/> PDF</button><button type="button" onClick={() => void apiDownload(`/ai/drafts/${row.id}/export/?format=docx`, `kalanpro-${row.id}.docx`)} className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-bold text-slate-600 hover:border-brand-200 hover:text-brand-600"><Download size={13}/> Word</button></div>
    <p className="mt-3 text-[10px] text-slate-400">Mis à jour le {new Date(row.updated_at).toLocaleString("fr-FR")}</p>
  </article>;
}
