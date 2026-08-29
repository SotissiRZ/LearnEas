"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  PlayCircle, CheckCircle2, Circle, Lock, ChevronLeft, FileText,
  Download, MessageSquare, Menu, X,
} from "lucide-react";
import { Course, Lesson, Section, CourseEnrollment } from "@/types";
import { api, formatDuration } from "@/lib/api";
import ProgressBar from "@/components/ui/ProgressBar";
import PdfViewer from "@/components/ui/PdfViewer";
import VideoPlayer from "@/components/ui/VideoPlayer";
import { useAuth } from "@/hooks/useAuth";

export default function LearnClient({ course }: { course: Course }) {
  const { user } = useAuth();
  const [enrollment, setEnrollment] = useState<CourseEnrollment | null>(null);
  const [activeLesson, setActiveLesson] = useState<Lesson | null>(null);
  const [completedIds, setCompletedIds] = useState<Set<number>>(new Set());
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [tab, setTab] = useState<"resources" | "discussion" | "transcript">("resources");

  const allLessons = (course.sections || []).flatMap((s) => s.lessons);

  useEffect(() => {
    if (!user) return;
    api.get<{ results: CourseEnrollment[] }>("/enrollments/my-courses/").then((data) => {
      const found = (data as any).results
        ? (data as any).results.find((e: CourseEnrollment) => e.course.id === course.id)
        : null;
      setEnrollment(found || null);
    }).catch(() => {});
  }, [user, course.id]);

  useEffect(() => {
    if (allLessons.length && !activeLesson) {
      setActiveLesson(allLessons.find((l) => !l.locked) || allLessons[0]);
    }
  }, [allLessons, activeLesson]);

  async function markComplete(lesson: Lesson) {
    if (!enrollment) return;
    try {
      const updated = await api.post<CourseEnrollment>(
        `/enrollments/my-courses/${enrollment.id}/mark_lesson_complete/`,
        { lesson_id: lesson.id }
      );
      setEnrollment(updated);
      setCompletedIds((prev) => new Set(prev).add(lesson.id));
    } catch {
      /* noop */
    }
  }

  if (!course.is_enrolled) {
    return (
      <div className="container-app flex min-h-[60vh] flex-col items-center justify-center gap-4 py-20 text-center">
        <Lock size={40} className="text-gray-300" />
        <h1 className="text-2xl font-bold">Vous n'avez pas encore accès à ce cours</h1>
        <Link href={`/courses/${course.slug}`} className="btn-primary">Voir la fiche du cours</Link>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen flex-col bg-gray-50 lg:flex-row">
      {/* SIDEBAR */}
      <aside className={`shrink-0 border-r border-gray-100 bg-white lg:w-96 ${sidebarOpen ? "block" : "hidden"} lg:block`}>
        <div className="flex items-center justify-between border-b border-gray-100 p-4">
          <Link href={`/courses/${course.slug}`} className="flex items-center gap-2 text-sm font-semibold text-gray-600">
            <ChevronLeft size={18} /> Retour à la fiche
          </Link>
          <button className="lg:hidden" onClick={() => setSidebarOpen(false)}><X size={18} /></button>
        </div>
        <div className="p-4">
          <h2 className="line-clamp-2 font-bold">{course.title}</h2>
          {enrollment && (
            <div className="mt-3">
              <div className="mb-1 flex justify-between text-xs text-gray-500">
                <span>Progression</span><span>{enrollment.progress_percent}%</span>
              </div>
              <ProgressBar value={enrollment.progress_percent} />
            </div>
          )}
        </div>
        <div className="max-h-[70vh] overflow-y-auto">
          {(course.sections || []).map((section: Section) => (
            <div key={section.id} className="border-t border-gray-100">
              <p className="bg-gray-50 px-4 py-2 text-xs font-bold uppercase tracking-wide text-gray-500">
                {section.title}
              </p>
              {section.lessons.map((lesson) => {
                const done = completedIds.has(lesson.id);
                const active = activeLesson?.id === lesson.id;
                return (
                  <button
                    key={lesson.id}
                    onClick={() => { setActiveLesson(lesson); setSidebarOpen(false); }}
                    className={`flex w-full items-center gap-3 px-4 py-3 text-left text-sm ${active ? "bg-brand-50" : "hover:bg-gray-50"}`}
                  >
                    {done ? (
                      <CheckCircle2 size={16} className="shrink-0 text-brand-600" />
                    ) : (
                      <Circle size={16} className="shrink-0 text-gray-300" />
                    )}
                    <span className={`flex-1 ${active ? "font-semibold text-brand-700" : ""}`}>{lesson.title}</span>
                    <span className="text-xs text-gray-400">{formatDuration(lesson.duration_minutes)}</span>
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </aside>

      {/* MAIN */}
      <div className="flex-1">
        <div className="flex items-center justify-between border-b border-gray-100 bg-white p-4 lg:hidden">
          <button onClick={() => setSidebarOpen(true)} className="flex items-center gap-2 text-sm font-semibold">
            <Menu size={18} /> Programme
          </button>
        </div>

        <div className="aspect-video w-full bg-black">
          {activeLesson?.video_url || activeLesson?.video_file ? (
            <VideoPlayer
              key={activeLesson.id}
              src={(activeLesson.video_url || activeLesson.video_file) as string}
              poster={course.thumbnail}
              title={activeLesson.title}
              subtitlesUrl={activeLesson.subtitles_file}
              onEnded={() => activeLesson && markComplete(activeLesson)}
            />
          ) : (
            <div className="grid h-full place-items-center text-white/50">
              <PlayCircle size={56} />
            </div>
          )}
        </div>

        <div className="container-app py-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h1 className="text-xl font-bold">{activeLesson?.title}</h1>
            {activeLesson && (
              <button onClick={() => markComplete(activeLesson)} className="btn-outline !py-1.5 !text-xs">
                <CheckCircle2 size={14} /> Marquer comme terminé
              </button>
            )}
          </div>
          {activeLesson?.description && <p className="mt-2 text-sm text-gray-600">{activeLesson.description}</p>}

          <div className="mt-6 flex gap-4 border-b border-gray-100 text-sm font-semibold">
            <button
              onClick={() => setTab("resources")}
              className={`flex items-center gap-1 border-b-2 pb-3 ${tab === "resources" ? "border-brand-600 text-brand-700" : "border-transparent text-gray-400"}`}
            >
              <FileText size={16} /> Ressources
            </button>
            <button
              onClick={() => setTab("discussion")}
              className={`flex items-center gap-1 border-b-2 pb-3 ${tab === "discussion" ? "border-brand-600 text-brand-700" : "border-transparent text-gray-400"}`}
            >
              <MessageSquare size={16} /> Discussion
            </button>
            <button
              onClick={() => setTab("transcript")}
              className={`flex items-center gap-1 border-b-2 pb-3 ${tab === "transcript" ? "border-brand-600 text-brand-700" : "border-transparent text-gray-400"}`}
            >
              <FileText size={16} /> Transcription
            </button>
          </div>

          <div className="py-6">
            {tab === "resources" ? (
              <div className="flex flex-col gap-2">
                {(course.pdf_resources || []).length === 0 && (
                  <p className="text-sm text-gray-500">Aucune ressource PDF pour ce cours.</p>
                )}
                {(course.pdf_resources || []).map((pdf) => (
                  <div key={pdf.id} className="card flex items-center justify-between p-3 text-sm">
                    <span className="flex items-center gap-2"><FileText size={16} className="text-amber-600" /> {pdf.title}</span>
                    {pdf.file && <PdfViewer url={pdf.file} title={pdf.title} />}
                  </div>
                ))}
              </div>
            ) : tab === "discussion" ? (
              <p className="text-sm text-gray-500">Posez vos questions à l'instructeur depuis l'espace Avis & questions.</p>
            ) : (
              <div className="card p-5 text-sm leading-7 text-gray-700">
                {activeLesson?.transcript ? <div className="whitespace-pre-wrap">{activeLesson.transcript}</div> : <p className="text-gray-500">Aucune transcription n'est disponible pour cette leçon.</p>}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
