"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  CalendarDays,
  CheckCircle2,
  ExternalLink,
  FileText,
  Loader2,
  PlayCircle,
  ShieldCheck,
  Users,
  Video,
} from "lucide-react";
import { api, ApiError, formatDuration } from "@/lib/api";
import CurrencyPrice from "@/components/ui/CurrencyPrice";
import { Course, InteractiveFormation, PDFProduct } from "@/types";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import GuardScreen from "@/components/ui/GuardScreen";
import CourseCurriculum from "@/components/course/CourseCurriculum";
import PdfViewer from "@/components/ui/PdfViewer";

function endpointFor(type: string, slug: string) {
  if (type === "course") return `/catalog/courses/${slug}/`;
  if (type === "pdf") return `/catalog/pdfs/${slug}/`;
  if (type === "formation") return `/formations/${slug}/`;
  return null;
}

export default function AdminContentReviewPage() {
  const params = useParams<{ type: string; slug: string }>();
  const { ready } = useAuthGuard({ roles: ["admin"], redirectTo: "/dashboard/admin" });
  const [resource, setResource] = useState<Course | PDFProduct | InteractiveFormation | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!ready) return;
    const endpoint = endpointFor(params.type, params.slug);
    if (!endpoint) { setError("Type de contenu inconnu."); return; }
    setError("");
    api.get<Course | PDFProduct | InteractiveFormation>(endpoint)
      .then(setResource)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Impossible de charger ce contenu."));
  }, [ready, params.type, params.slug]);

  if (!ready) return <GuardScreen />;
  if (error) return <div className="container-app py-12"><ReviewBack /><div className="mt-5 rounded-2xl border border-red-100 bg-red-50 p-5 text-sm text-red-700">{error}</div></div>;
  if (!resource) return <div className="container-app py-16 text-center text-sm text-gray-400"><Loader2 className="mx-auto mb-3 animate-spin" />Chargement du contenu à vérifier...</div>;

  return (
    <div className="min-h-screen bg-slate-50/70 py-8 sm:py-10">
      <div className="container-app">
        <ReviewBack />
        <div className="mt-5 overflow-hidden rounded-3xl border border-gray-200 bg-white shadow-soft">
          <div className="border-b border-gray-100 bg-gradient-to-r from-slate-950 via-slate-900 to-emerald-950 px-5 py-6 text-white sm:px-8 sm:py-8">
            <div className="flex flex-wrap items-start justify-between gap-5">
              <div className="max-w-3xl">
                <div className="mb-3 flex flex-wrap items-center gap-2">
                  <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-400/20 px-3 py-1 text-xs font-semibold text-emerald-200"><ShieldCheck size={14} /> Vérification administrateur</span>
                  <span className={`rounded-full px-3 py-1 text-xs font-semibold ${resource.published ? "bg-white/10 text-white" : "bg-amber-400/20 text-amber-200"}`}>{resource.published ? "Publié" : "Non publié"}</span>
                </div>
                <h1 className="text-2xl font-extrabold leading-tight sm:text-3xl">{resource.title}</h1>
                <p className="mt-2 text-sm text-slate-300">Vous disposez d'un accès de contrôle complet, même si ce contenu n'est pas publié ou acheté.</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-right backdrop-blur">
                <p className="text-[11px] uppercase tracking-wider text-slate-400">Type</p>
                <p className="mt-1 font-bold">{params.type === "course" ? "Cours vidéo" : params.type === "pdf" ? "Document PDF" : "Formation interactive"}</p>
              </div>
            </div>
          </div>

          <div className="p-5 sm:p-8">
            {params.type === "course" ? <CourseReview course={resource as Course} /> : params.type === "pdf" ? <PdfReview pdf={resource as PDFProduct} /> : <FormationReview formation={resource as InteractiveFormation} />}
          </div>
        </div>
      </div>
    </div>
  );
}

function ReviewBack() {
  return <Link href="/dashboard/admin?tab=content" className="inline-flex items-center gap-2 text-sm font-semibold text-gray-600 transition hover:text-brand-700"><ArrowLeft size={16} /> Retour aux contenus</Link>;
}

function CourseReview({ course }: { course: Course }) {
  return <div className="grid gap-7 xl:grid-cols-[1fr_300px]">
    <div>
      <div className="mb-5 flex items-center justify-between gap-3"><div><h2 className="text-xl font-extrabold">Lecture et ressources</h2><p className="mt-1 text-sm text-gray-500">Ouvrez chaque leçon et chaque PDF pour contrôler le contenu réel.</p></div></div>
      <CourseCurriculum course={course} />
    </div>
    <aside className="space-y-4">
      <ReviewMetric icon={<PlayCircle size={17} />} label="Leçons" value={`${course.total_lessons}`} />
      <ReviewMetric icon={<FileText size={17} />} label="Ressources PDF" value={`${course.pdf_resources?.length || 0}`} />
      <ReviewMetric icon={<Users size={17} />} label="Étudiants" value={`${course.students_count}`} />
      <ReviewMetric icon={<CheckCircle2 size={17} />} label="Durée" value={formatDuration(course.total_duration_minutes)} />
      <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4 text-sm"><p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Instructeur</p><p className="mt-2 font-bold text-ink">{course.instructor.full_name}</p><p className="mt-1 text-gray-500"><CurrencyPrice value={course.effective_price} /></p></div>
    </aside>
  </div>;
}

function PdfReview({ pdf }: { pdf: PDFProduct }) {
  return <div className="grid gap-7 lg:grid-cols-[1fr_320px]">
    <div className="rounded-2xl border border-gray-200 bg-slate-50 p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-xl font-extrabold">Document complet</h2><p className="mt-1 text-sm text-gray-500">Le fichier original est déverrouillé pour l'administrateur.</p></div>{pdf.file ? <PdfViewer url={pdf.file} title={`${pdf.title} · vérification admin`} /> : null}</div>
      {!pdf.file && <div className="mt-5 rounded-xl border border-amber-100 bg-amber-50 p-4 text-sm text-amber-800">Aucun fichier PDF complet n'est attaché à ce contenu.</div>}
      {pdf.preview_file && <div className="mt-5 border-t border-gray-200 pt-5"><p className="mb-3 text-sm font-semibold">Aperçu public configuré</p><PdfViewer url={pdf.preview_file} title={`${pdf.title} · aperçu public`} /></div>}
      {pdf.description && <div className="mt-6 rounded-xl bg-white p-5 text-sm leading-7 text-gray-600 shadow-sm"><h3 className="mb-2 font-bold text-ink">Description</h3><p className="whitespace-pre-line">{pdf.description}</p></div>}
    </div>
    <aside className="space-y-4">
      <ReviewMetric icon={<FileText size={17} />} label="Pages" value={`${pdf.page_count}`} />
      <ReviewMetric icon={<Users size={17} />} label="Achats" value={`${pdf.downloads_count}`} />
      <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4 text-sm"><p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Instructeur</p><p className="mt-2 font-bold text-ink">{pdf.instructor.full_name}</p><p className="mt-1 text-gray-500"><CurrencyPrice value={pdf.price} /></p></div>
    </aside>
  </div>;
}

function FormationReview({ formation }: { formation: InteractiveFormation }) {
  return <div className="grid gap-7 xl:grid-cols-[1fr_300px]">
    <div>
      <div className="mb-5"><h2 className="text-xl font-extrabold">Planning et contrôle des séances</h2><p className="mt-1 text-sm text-gray-500">L'administrateur peut ouvrir une salle de séance pour vérification lorsque celle-ci est disponible.</p></div>
      <div className="grid gap-3">
        {(formation.sessions || []).map((session) => <div key={session.id} className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-gray-100 bg-white p-4 shadow-sm"><div className="flex items-start gap-3"><span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-violet-50 text-violet-700"><Video size={18} /></span><div><p className="font-bold">Séance {session.session_number}</p><p className="mt-1 flex items-center gap-1 text-xs text-gray-500"><CalendarDays size={12} /> {new Date(session.scheduled_at).toLocaleString("fr-FR")} · {formatDuration(session.duration_minutes)}</p></div></div>{session.can_join ? <Link href={`/live/session/${session.id}`} className="btn-primary !py-2 !text-xs"><ExternalLink size={14} /> Ouvrir la salle</Link> : <span className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-500">{session.completed ? "Terminée" : "Indisponible"}</span>}</div>)}
        {(formation.sessions || []).length === 0 && <div className="rounded-2xl border border-dashed border-gray-200 p-8 text-center text-sm text-gray-400">Aucune séance planifiée.</div>}
      </div>
      {formation.description && <div className="mt-6 rounded-2xl border border-gray-100 bg-gray-50 p-5 text-sm leading-7 text-gray-600"><h3 className="mb-2 font-bold text-ink">Description</h3><p className="whitespace-pre-line">{formation.description}</p></div>}
    </div>
    <aside className="space-y-4">
      <ReviewMetric icon={<Video size={17} />} label="Séances" value={`${formation.num_sessions}`} />
      <ReviewMetric icon={<Users size={17} />} label="Inscrits" value={`${formation.students_count}/${formation.max_students}`} />
      <ReviewMetric icon={<CheckCircle2 size={17} />} label="Statut" value={formation.status} />
      <div className="rounded-2xl border border-gray-100 bg-gray-50 p-4 text-sm"><p className="text-xs font-semibold uppercase tracking-wide text-gray-400">Instructeur</p><p className="mt-2 font-bold text-ink">{formation.instructor.full_name}</p><p className="mt-1 text-gray-500"><CurrencyPrice value={formation.price} /></p></div>
    </aside>
  </div>;
}

function ReviewMetric({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return <div className="flex items-center gap-3 rounded-2xl border border-gray-100 bg-white p-4 shadow-sm"><span className="grid h-10 w-10 place-items-center rounded-xl bg-brand-50 text-brand-700">{icon}</span><div><p className="text-[11px] font-semibold uppercase tracking-wide text-gray-400">{label}</p><p className="mt-0.5 font-extrabold text-ink">{value}</p></div></div>;
}
