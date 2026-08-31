"use client";

import { useMemo, useState } from "react";
import {
  ChevronDown,
  Clock,
  Eye,
  FileText,
  Lock,
  PlayCircle,
  ShieldCheck,
  X,
} from "lucide-react";
import { Course, Lesson } from "@/types";
import { formatDuration } from "@/lib/api";
import { useAuthenticatedResource } from "@/hooks/useAuthenticatedResource";
import { useAuth } from "@/hooks/useAuth";
import PdfViewer from "@/components/ui/PdfViewer";
import VideoPlayer from "@/components/ui/VideoPlayer";

export default function CourseCurriculum({ course: initialCourse }: { course: Course }) {
  const course = useAuthenticatedResource<Course>(`/catalog/courses/${initialCourse.slug}/`, initialCourse);
  const { user } = useAuth();
  const sections = course.sections || [];
  const pdfResources = course.pdf_resources || [];
  const [open, setOpen] = useState<number | null>(sections[0]?.id ?? null);
  const [activeLesson, setActiveLesson] = useState<Lesson | null>(null);

  const canVerifyEverything = user?.role === "admin";
  const unlockedCount = useMemo(
    () => sections.flatMap((section) => section.lessons).filter((lesson) => !lesson.locked).length,
    [sections]
  );

  function playableSource(lesson: Lesson) {
    return lesson.video_url || lesson.video_file || null;
  }

  return (
    <div className="flex flex-col gap-5">
      {canVerifyEverything && (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
          <span className="flex items-center gap-2 font-semibold">
            <ShieldCheck size={17} /> Mode vérification administrateur
          </span>
          <span className="text-xs text-emerald-700">{unlockedCount} leçon(s) déverrouillée(s) pour contrôle.</span>
        </div>
      )}

      <div className="overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-card">
        {sections.map((section, sectionIndex) => (
          <div key={section.id} className={sectionIndex ? "border-t border-gray-100" : ""}>
            <button
              type="button"
              onClick={() => setOpen(open === section.id ? null : section.id)}
              className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left transition hover:bg-gray-50"
            >
              <div className="min-w-0">
                <p className="font-bold text-ink">{section.title}</p>
                <p className="mt-1 text-xs text-gray-500">
                  {section.lessons.length} vidéo{section.lessons.length > 1 ? "s" : ""} · {formatDuration(section.duration_minutes)}
                </p>
              </div>
              <ChevronDown
                size={18}
                className={`shrink-0 text-gray-400 transition-transform ${open === section.id ? "rotate-180" : ""}`}
              />
            </button>

            {open === section.id && (
              <div className="border-t border-gray-100 bg-gray-50/50 px-2 py-2 sm:px-3">
                {section.lessons.map((lesson, index) => {
                  const source = playableSource(lesson);
                  const canPlay = !lesson.locked && Boolean(source);
                  return (
                    <div
                      key={lesson.id}
                      className="group mb-1 flex min-h-14 items-center gap-3 rounded-xl px-3 py-2.5 transition last:mb-0 hover:bg-white hover:shadow-sm"
                    >
                      <div className={`grid h-8 w-8 shrink-0 place-items-center rounded-full ${lesson.locked ? "bg-gray-100 text-gray-400" : "bg-brand-50 text-brand-700"}`}>
                        {lesson.locked ? <Lock size={15} /> : <PlayCircle size={16} />}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className={`text-sm font-medium ${lesson.locked ? "text-gray-500" : "text-ink"}`}>
                          {index + 1}. {lesson.title}
                        </p>
                        <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-gray-400">
                          <span className="flex items-center gap-1"><Clock size={11} /> {formatDuration(lesson.duration_minutes)}</span>
                          {lesson.is_preview && <span className="badge !px-2 !py-0.5 bg-brand-50 text-brand-700">Aperçu gratuit</span>}
                          {canVerifyEverything && !lesson.locked && <span className="badge !px-2 !py-0.5 bg-emerald-50 text-emerald-700">Vérifiable</span>}
                        </div>
                      </div>
                      {canPlay ? (
                        <button
                          type="button"
                          onClick={() => setActiveLesson(lesson)}
                          className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-brand-200 bg-white px-3 py-2 text-xs font-semibold text-brand-700 transition hover:border-brand-400 hover:bg-brand-50"
                        >
                          <Eye size={14} /> Lire
                        </button>
                      ) : lesson.locked ? (
                        <span className="hidden text-[11px] text-gray-400 sm:inline">Après achat</span>
                      ) : (
                        <span className="hidden text-[11px] text-amber-600 sm:inline">Vidéo indisponible</span>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        ))}
      </div>

      {pdfResources.length > 0 && (
        <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-card">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h3 className="flex items-center gap-2 font-bold"><FileText size={18} className="text-amber-600" /> Ressources PDF incluses</h3>
            <span className="text-xs text-gray-400">{pdfResources.length} document(s)</span>
          </div>
          <div className="grid gap-2">
            {pdfResources.map((pdf) => (
              <div key={pdf.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-gray-100 bg-gray-50/60 px-4 py-3 text-sm">
                <div className="flex min-w-0 items-center gap-3">
                  <div className={`grid h-9 w-9 shrink-0 place-items-center rounded-lg ${pdf.locked ? "bg-gray-100 text-gray-400" : "bg-amber-50 text-amber-700"}`}>
                    {pdf.locked ? <Lock size={15} /> : <FileText size={16} />}
                  </div>
                  <div className="min-w-0">
                    <p className={`truncate font-medium ${pdf.locked ? "text-gray-500" : "text-ink"}`}>{pdf.title}</p>
                    <p className="mt-0.5 text-[11px] text-gray-400">{pdf.page_count} page(s){pdf.is_free_sample ? " · extrait gratuit" : ""}</p>
                  </div>
                </div>
                {!pdf.locked && pdf.file ? <PdfViewer url={pdf.file} title={pdf.title} /> : <span className="text-xs text-gray-400">Verrouillé</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {activeLesson && playableSource(activeLesson) && (
        <div className="fixed inset-0 z-[70] flex items-center justify-center bg-black/80 p-2 sm:p-6" onClick={() => setActiveLesson(null)}>
          <div className="flex max-h-[94vh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl bg-white shadow-2xl" onClick={(event) => event.stopPropagation()}>
            <div className="flex items-center justify-between gap-4 border-b border-gray-100 px-4 py-3 sm:px-5">
              <div className="min-w-0">
                <p className="truncate text-sm font-bold text-ink">{activeLesson.title}</p>
                <p className="text-[11px] text-gray-400">{activeLesson.is_preview ? "Aperçu gratuit" : canVerifyEverything ? "Vérification administrateur" : "Contenu du cours"}</p>
              </div>
              <button type="button" onClick={() => setActiveLesson(null)} className="rounded-lg p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-700" aria-label="Fermer la vidéo"><X size={19} /></button>
            </div>
            <div className="aspect-video min-h-0 w-full bg-black">
              <VideoPlayer
                key={activeLesson.id}
                src={playableSource(activeLesson) as string}
                poster={course.thumbnail}
                title={activeLesson.title}
                subtitlesUrl={activeLesson.subtitles_file}
              />
            </div>
            {activeLesson.description && <p className="border-t border-gray-100 px-5 py-3 text-sm text-gray-600">{activeLesson.description}</p>}
          </div>
        </div>
      )}
    </div>
  );
}
