"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Award, CheckCircle2, Clock3, ExternalLink, FileUp, GitBranch, Loader2, Send, ShieldCheck, UploadCloud } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { ProjectAssignment, ProjectSubmissionSummary } from "@/types";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import GuardScreen from "@/components/ui/GuardScreen";
import DashboardNav from "@/components/dashboard/DashboardNav";

const STATUS: Record<string, { label: string; cls: string }> = {
  draft: { label: "Brouillon", cls: "bg-gray-100 text-gray-600" },
  submitted: { label: "En correction", cls: "bg-blue-50 text-blue-700" },
  changes_requested: { label: "À corriger", cls: "bg-amber-50 text-amber-700" },
  approved: { label: "Validé", cls: "bg-emerald-50 text-emerald-700" },
  rejected: { label: "Refusé", cls: "bg-red-50 text-red-700" },
};

export default function StudentProjectsPage() {
  const { ready } = useAuthGuard();
  const [rows, setRows] = useState<ProjectAssignment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [editing, setEditing] = useState<number | null>(null);

  async function load() {
    setLoading(true); setError("");
    try { setRows(await api.get<ProjectAssignment[]>("/projects/assignments/")); }
    catch (e) { setError(e instanceof ApiError ? e.message : "Impossible de charger vos projets."); }
    finally { setLoading(false); }
  }
  useEffect(() => { if (ready) void load(); }, [ready]);
  const pending = useMemo(() => rows.filter((r) => !r.submission || r.submission.status !== "approved").length, [rows]);

  async function publishPortfolio(submission: ProjectSubmissionSummary) {
    setError(""); setMessage("");
    try {
      await api.post(`/projects/submissions/${submission.id}/publish-portfolio/`, {});
      setMessage("Projet ajouté à votre portfolio public. Vous pouvez maintenant personnaliser sa présentation.");
    } catch (e) { setError(e instanceof ApiError ? e.message : "Publication impossible."); }
  }

  if (!ready) return <GuardScreen />;
  return <div className="container-app py-10">
    <DashboardNav role="student" />
    <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div><h1 className="text-2xl font-bold">Mes projets pratiques</h1><p className="mt-1 text-sm text-gray-500">Construisez des preuves de compétences corrigées par vos instructeurs.</p></div>
      <div className="flex gap-2"><span className="badge bg-brand-50 text-brand-700">{pending} à terminer</span><Link href="/dashboard/student/portfolio" className="btn-outline !py-2 !text-xs">Mon portfolio</Link></div>
    </div>
    {error && <div className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</div>}
    {message && <div className="mb-4 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-700">{message}</div>}
    {loading ? <div className="card p-10 text-center text-gray-400"><Loader2 className="mx-auto mb-2 animate-spin" />Chargement...</div> : rows.length === 0 ? <div className="card p-10 text-center text-gray-500"><Award className="mx-auto mb-3 text-gray-300" />Aucun projet pratique n'est encore associé à vos cours.</div> : <div className="space-y-5">
      {rows.map((assignment) => <article key={assignment.id} className="card overflow-hidden">
        <div className="p-5 sm:p-6">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0"><p className="text-xs font-semibold uppercase tracking-wide text-brand-700">{assignment.course_title}</p><h2 className="mt-1 text-lg font-bold">{assignment.title}</h2><p className="mt-2 max-w-3xl whitespace-pre-wrap text-sm leading-6 text-gray-600">{assignment.brief}</p></div>
            <div className="flex flex-wrap gap-2">{assignment.required_for_certificate && <span className="badge bg-violet-50 text-violet-700"><ShieldCheck size={12}/> Requis pour certificat</span>}{assignment.submission && <span className={`badge ${STATUS[assignment.submission.status]?.cls || "bg-gray-100"}`}>{STATUS[assignment.submission.status]?.label || assignment.submission.status}</span>}</div>
          </div>
          <div className="mt-4 grid gap-4 lg:grid-cols-3">
            <Info title="Livrables" values={assignment.deliverables} fallback="Suivez le brief du projet." />
            <Info title="Compétences" values={assignment.skills} fallback="Compétences du cours." />
            <div className="rounded-xl bg-gray-50 p-4 text-xs text-gray-600"><p className="font-semibold text-gray-900">Évaluation</p><p className="mt-2">Validation : {assignment.passing_score}/{assignment.max_score}</p>{assignment.due_at && <p className="mt-1 flex items-center gap-1"><Clock3 size={12}/> Échéance : {new Date(assignment.due_at).toLocaleDateString("fr-FR")}</p>}</div>
          </div>
          {assignment.instructions && <details className="mt-4 rounded-xl border border-gray-100 p-4"><summary className="cursor-pointer text-sm font-semibold">Instructions détaillées</summary><p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-gray-600">{assignment.instructions}</p></details>}
          {assignment.submission?.instructor_feedback && <div className={`mt-4 rounded-xl p-4 text-sm ${assignment.submission.status === "approved" ? "bg-emerald-50 text-emerald-800" : "bg-amber-50 text-amber-900"}`}><p className="font-semibold">Retour de l'instructeur</p><p className="mt-1 whitespace-pre-wrap">{assignment.submission.instructor_feedback}</p>{assignment.submission.score != null && <p className="mt-2 font-bold">Note : {assignment.submission.score}/{assignment.max_score}</p>}</div>}
          <div className="mt-5 flex flex-wrap gap-2">
            {(!assignment.submission || assignment.submission.status === "draft" || assignment.submission.can_resubmit) && <button onClick={() => setEditing(editing === assignment.id ? null : assignment.id)} className="btn-primary !py-2 !text-xs"><UploadCloud size={14}/>{assignment.submission ? "Modifier ma remise" : "Commencer le projet"}</button>}
            {assignment.submission?.status === "approved" && <button onClick={() => void publishPortfolio(assignment.submission!)} className="btn-primary !py-2 !text-xs"><ShieldCheck size={14}/> Ajouter au portfolio</button>}
            <Link href={`/learn/${assignment.course_slug}`} className="btn-outline !py-2 !text-xs">Retour au cours</Link>
          </div>
        </div>
        {editing === assignment.id && <SubmissionForm assignment={assignment} onDone={async () => { setEditing(null); await load(); }} onError={setError} />}
      </article>)}
    </div>}
  </div>;
}

function Info({title, values, fallback}:{title:string;values:string[];fallback:string}) { return <div className="rounded-xl bg-gray-50 p-4 text-xs text-gray-600"><p className="font-semibold text-gray-900">{title}</p>{values?.length ? <ul className="mt-2 space-y-1">{values.map((v)=><li key={v}>• {v}</li>)}</ul> : <p className="mt-2">{fallback}</p>}</div> }

function SubmissionForm({assignment,onDone,onError}:{assignment:ProjectAssignment;onDone:()=>Promise<void>;onError:(v:string)=>void}) {
  const existing = assignment.submission;
  const [form,setForm] = useState({title:existing?.title||assignment.title,summary:existing?.summary||"",external_url:existing?.external_url||"",repository_url:existing?.repository_url||"",skills:(existing?.skills||assignment.skills||[]).join(", ")});
  const [artifact,setArtifact] = useState<File|null>(null); const [cover,setCover]=useState<File|null>(null); const [busy,setBusy]=useState(false); const [saved,setSaved]=useState<ProjectSubmissionSummary|null>(existing||null);
  function set(k:keyof typeof form,v:string){setForm(x=>({...x,[k]:v}))}
  async function saveAndMaybeSubmit(submit:boolean){ setBusy(true); onError(""); try { const fd=new FormData(); fd.append("assignment",String(assignment.id)); fd.append("title",form.title);fd.append("summary",form.summary);fd.append("external_url",form.external_url);fd.append("repository_url",form.repository_url);fd.append("skills",JSON.stringify(form.skills.split(",").map(x=>x.trim()).filter(Boolean))); if(artifact)fd.append("artifact_file",artifact);if(cover)fd.append("cover_image",cover);
      let row:ProjectSubmissionSummary; if(saved){ row=await api.patch<ProjectSubmissionSummary>(`/projects/submissions/${saved.id}/`,fd);} else { row=await api.post<ProjectSubmissionSummary>("/projects/submissions/",fd); setSaved(row); }
      if(submit){ row=await api.post<ProjectSubmissionSummary>(`/projects/submissions/${row.id}/submit/`,{}); }
      await onDone();
    } catch(e){onError(e instanceof ApiError?e.message:"Impossible d'enregistrer la remise.");} finally{setBusy(false)} }
  return <div className="border-t border-gray-100 bg-gray-50/70 p-5 sm:p-6"><div className="grid gap-4 lg:grid-cols-2"><Field label="Titre du projet"><input value={form.title} onChange={e=>set("title",e.target.value)} className="input-admin w-full" /></Field><Field label="Compétences (séparées par des virgules)"><input value={form.skills} onChange={e=>set("skills",e.target.value)} className="input-admin w-full" placeholder="Excel, Power BI, Analyse"/></Field></div><Field label="Présentation / démarche"><textarea rows={6} value={form.summary} onChange={e=>set("summary",e.target.value)} className="input-admin w-full" placeholder="Expliquez ce que vous avez construit, vos choix et le résultat obtenu."/></Field><div className="mt-4 grid gap-4 lg:grid-cols-2"><Field label="Lien de démonstration"><div className="relative"><ExternalLink size={14} className="absolute left-3 top-3 text-gray-400"/><input type="url" value={form.external_url} onChange={e=>set("external_url",e.target.value)} className="input-admin w-full pl-9" placeholder="https://..."/></div></Field><Field label="Dépôt de code / source"><div className="relative"><GitBranch size={14} className="absolute left-3 top-3 text-gray-400"/><input type="url" value={form.repository_url} onChange={e=>set("repository_url",e.target.value)} className="input-admin w-full pl-9" placeholder="https://github.com/..."/></div></Field></div><div className="mt-4 grid gap-4 lg:grid-cols-2"><FilePicker label="Fichier du projet" icon={<FileUp size={15}/>} accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.zip,.txt,.csv,.png,.jpg,.jpeg,.webp" file={artifact} setFile={setArtifact}/><FilePicker label="Image de couverture du portfolio" icon={<UploadCloud size={15}/>} accept="image/*" file={cover} setFile={setCover}/></div><div className="mt-5 flex flex-wrap gap-2"><button disabled={busy} onClick={()=>void saveAndMaybeSubmit(false)} className="btn-outline !py-2 !text-xs">{busy?<Loader2 size={14} className="animate-spin"/>:null}Enregistrer le brouillon</button><button disabled={busy} onClick={()=>void saveAndMaybeSubmit(true)} className="btn-primary !py-2 !text-xs"><Send size={14}/> Remettre à l'instructeur</button></div></div>
}
function Field({label,children}:{label:string;children:React.ReactNode}){return <label className="mt-4 block"><span className="mb-1.5 block text-xs font-semibold text-gray-700">{label}</span>{children}</label>}
function FilePicker({label,icon,accept,file,setFile}:{label:string;icon:React.ReactNode;accept:string;file:File|null;setFile:(f:File|null)=>void}){return <label className="block"><span className="mb-1.5 block text-xs font-semibold text-gray-700">{label}</span><span className="flex cursor-pointer items-center gap-2 rounded-xl border border-dashed border-gray-300 bg-white p-3 text-xs text-gray-500">{icon}{file?file.name:"Choisir un fichier"}<input type="file" accept={accept} className="hidden" onChange={e=>setFile(e.target.files?.[0]||null)}/></span></label>}
