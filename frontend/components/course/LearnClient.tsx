"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type Dispatch, type SetStateAction } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  BriefcaseBusiness,
  CheckCircle2,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Circle,
  Clock,
  Download,
  Edit3,
  FileText,
  Lock,
  Menu,
  MessageSquare,
  PlayCircle,
  Search,
  Send,
  Trash2,
  X,
} from "lucide-react";
import { Course, CourseEnrollment, Lesson, LessonNote, Paginated, Section, ProjectAssignment } from "@/types";
import { api, ApiError, formatDuration } from "@/lib/api";
import ProgressBar from "@/components/ui/ProgressBar";
import PdfViewer from "@/components/ui/PdfViewer";
import VideoPlayer, { VideoPlayerHandle } from "@/components/ui/VideoPlayer";
import { useAuth } from "@/hooks/useAuth";
import { publishAIContext } from "@/lib/aiContext";

type LearningTab = "overview" | "transcript" | "notes" | "qna" | "resources" | "project";
type TranscriptScope = "video" | "course";

type LessonComment = {
  id: number;
  lesson: number;
  content: string;
  created_at: string;
  user: { id: number; full_name: string; avatar?: string | null };
  replies?: LessonComment[];
};

type TranscriptSegment = {
  lesson: Lesson;
  seconds: number | null;
  text: string;
};

function unwrap<T>(value: Paginated<T> | T[]): T[] {
  return Array.isArray(value) ? value : value.results || [];
}

function formatSeconds(seconds: number): string {
  const safe = Math.max(0, Math.floor(seconds || 0));
  const h = Math.floor(safe / 3600);
  const m = Math.floor((safe % 3600) / 60);
  const s = safe % 60;
  return h > 0 ? `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}` : `${m}:${String(s).padStart(2, "0")}`;
}

function parseTranscript(lesson: Lesson): TranscriptSegment[] {
  const value = String(lesson.transcript || "").trim();
  if (!value) return [];
  const rows = value.split(/\n+/).map((line) => line.trim()).filter(Boolean);
  return rows.map((line) => {
    const match = line.match(/^\s*\[?(\d{1,2}):(\d{2})(?::(\d{2}))?\]?\s*(?:[-–—]\s*)?(.*)$/);
    if (!match) return { lesson, seconds: null, text: line };
    const first = Number(match[1]);
    const second = Number(match[2]);
    const third = match[3] == null ? null : Number(match[3]);
    const seconds = third == null ? first * 60 + second : first * 3600 + second * 60 + third;
    return { lesson, seconds, text: (match[4] || line).trim() };
  });
}

export default function LearnClient({ course }: { course: Course }) {
  const { user } = useAuth();
  const playerRef = useRef<VideoPlayerHandle | null>(null);
  const mainRef = useRef<HTMLDivElement | null>(null);

  const [enrollment, setEnrollment] = useState<CourseEnrollment | null>(null);
  const [activeLesson, setActiveLesson] = useState<Lesson | null>(null);
  const [completedIds, setCompletedIds] = useState<Set<number>>(new Set());
  const [resumePositions, setResumePositions] = useState<Record<number, number>>({});
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [openSections, setOpenSections] = useState<Set<number>>(() => new Set((course.sections || []).map((section) => section.id)));
  const [tab, setTab] = useState<LearningTab>("overview");
  const [autoplay, setAutoplay] = useState(true);
  const [currentTime, setCurrentTime] = useState(0);
  const [videoDuration, setVideoDuration] = useState(0);
  const [seekTarget, setSeekTarget] = useState<{ lessonId: number; seconds: number } | null>(null);
  const [autoStartLesson, setAutoStartLesson] = useState(false);

  const [transcriptQuery, setTranscriptQuery] = useState("");
  const [transcriptScope, setTranscriptScope] = useState<TranscriptScope>("video");

  const [notes, setNotes] = useState<LessonNote[]>([]);
  const [noteScope, setNoteScope] = useState<"lesson" | "course">("lesson");
  const [noteDraft, setNoteDraft] = useState("");
  const [editingNoteId, setEditingNoteId] = useState<number | null>(null);
  const [editingNoteText, setEditingNoteText] = useState("");
  const [noteBusy, setNoteBusy] = useState(false);
  const [noteError, setNoteError] = useState("");

  const [comments, setComments] = useState<LessonComment[]>([]);
  const [questionDraft, setQuestionDraft] = useState("");
  const [questionBusy, setQuestionBusy] = useState(false);
  const [questionError, setQuestionError] = useState("");
  const [courseProjects, setCourseProjects] = useState<ProjectAssignment[]>([]);
  const [projectsLoading, setProjectsLoading] = useState(false);

  const allLessons = useMemo(
    () => (course.sections || []).flatMap((section) => section.lessons),
    [course.sections],
  );
  const currentIndex = activeLesson ? allLessons.findIndex((lesson) => lesson.id === activeLesson.id) : -1;
  const previousLesson = currentIndex > 0 ? allLessons[currentIndex - 1] : null;
  const nextLesson = currentIndex >= 0 && currentIndex < allLessons.length - 1 ? allLessons[currentIndex + 1] : null;

  useEffect(() => {
    try {
      const stored = localStorage.getItem("learneas_player_autoplay");
      if (stored != null) setAutoplay(stored !== "false");
      const sidebar = localStorage.getItem("learneas_player_sidebar");
      if (sidebar != null) setSidebarOpen(sidebar !== "false");
    } catch {
      // Storage peut être désactivé par le navigateur.
    }
  }, []);

  useEffect(() => {
    try { localStorage.setItem("learneas_player_autoplay", String(autoplay)); } catch {}
  }, [autoplay]);

  useEffect(() => {
    try { localStorage.setItem("learneas_player_sidebar", String(sidebarOpen)); } catch {}
  }, [sidebarOpen]);

  useEffect(() => {
    if (!user) return;
    api.get<Paginated<CourseEnrollment> | CourseEnrollment[]>("/enrollments/my-courses/").then((data) => {
      const found = unwrap(data).find((item) => item.course.id === course.id) || null;
      setEnrollment(found);
      if (found?.lesson_progress?.length) {
        setCompletedIds(new Set(found.lesson_progress.filter((item) => item.completed).map((item) => item.lesson)));
        setResumePositions(Object.fromEntries(found.lesson_progress.map((item) => [item.lesson, item.last_position_seconds || 0])));
      }
      if (found?.last_accessed_lesson) {
        const last = allLessons.find((lesson) => lesson.id === found.last_accessed_lesson && !lesson.locked);
        if (last) setActiveLesson(last);
      }
    }).catch(() => setEnrollment(null));
  }, [user, course.id, allLessons]);

  useEffect(() => {
    if (allLessons.length && !activeLesson) {
      setActiveLesson(allLessons.find((lesson) => !lesson.locked) || allLessons[0]);
    }
  }, [allLessons, activeLesson]);

  useEffect(() => {
    publishAIContext({
      kind: activeLesson ? "lesson" : "course-learning",
      path: typeof window !== "undefined" ? window.location.pathname : `/learn/${course.slug}`,
      course_slug: course.slug,
      lesson_id: activeLesson?.id,
      lesson_title: activeLesson?.title,
    });
  }, [course.slug, activeLesson?.id, activeLesson?.title]);

  const selectLesson = useCallback((lesson: Lesson, seconds?: number, autoStart = false) => {
    if (lesson.locked) return;
    setActiveLesson(lesson);
    setCurrentTime(seconds || 0);
    setVideoDuration(0);
    setMobileSidebarOpen(false);
    setSeekTarget(seconds != null ? { lessonId: lesson.id, seconds } : null);
    setAutoStartLesson(autoStart);
    window.setTimeout(() => mainRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }), 30);
  }, []);

  async function markComplete(lesson: Lesson) {
    if (!enrollment) {
      setCompletedIds((prev) => new Set(prev).add(lesson.id));
      return;
    }
    try {
      const updated = await api.post<CourseEnrollment>(
        `/enrollments/my-courses/${enrollment.id}/mark_lesson_complete/`,
        { lesson_id: lesson.id, watched_seconds: Math.floor(playerRef.current?.getCurrentTime() || currentTime) },
      );
      setEnrollment(updated);
      setCompletedIds((prev) => new Set(prev).add(lesson.id));
    } catch {
      // La lecture continue même si la synchronisation de progression échoue momentanément.
    }
  }

  const persistProgress = useCallback((seconds: number) => {
    if (!activeLesson) return;
    setResumePositions((prev) => ({ ...prev, [activeLesson.id]: Math.floor(seconds) }));
    if (!enrollment) return;
    void api.post(
      `/enrollments/my-courses/${enrollment.id}/update-lesson-progress/`,
      { lesson_id: activeLesson.id, watched_seconds: Math.floor(seconds) },
    ).catch(() => {});
  }, [activeLesson, enrollment]);

  async function handleEnded() {
    if (!activeLesson) return;
    await markComplete(activeLesson);
    if (autoplay && nextLesson && !nextLesson.locked) selectLesson(nextLesson, undefined, true);
  }

  const canRepairActiveVideo = Boolean(
    activeLesson?.video_file && user &&
    (user.role === "admin" || (user.role === "instructor" && user.id === course.instructor.id)),
  );

  async function repairActiveVideo() {
    const lesson = activeLesson;
    if (!lesson?.video_file || !canRepairActiveVideo) throw new Error("Cette vidéo ne peut pas être réparée depuis ce compte.");
    const queued = await api.post<{ task_id: string }>(`/catalog/lessons/${lesson.id}/repair-video/`, {});
    if (!queued.task_id) throw new Error("La tâche de réparation n'a pas pu être lancée.");

    const startedAt = Date.now();
    while (Date.now() - startedAt < 30 * 60 * 1000) {
      await new Promise((resolve) => window.setTimeout(resolve, 2500));
      const status = await api.get<{ state: string; video_file?: string | null; duration_minutes?: number; detail?: string }>(
        `/catalog/lessons/${lesson.id}/repair-video-status/${queued.task_id}/`,
      );
      if (status.state === "FAILURE") throw new Error(status.detail || "La conversion de la vidéo a échoué.");
      if (status.state === "SUCCESS") {
        if (!status.video_file) throw new Error(status.detail || "La vidéo réparée n'a pas pu être récupérée.");
        setActiveLesson((current) => current && current.id === lesson.id ? {
          ...current,
          video_file: status.video_file || current.video_file,
          duration_minutes: status.duration_minutes || current.duration_minutes,
        } : current);
        return;
      }
    }
    throw new Error("La conversion prend plus de 30 minutes. Elle continue en arrière-plan ; réessayez plus tard.");
  }

  const loadNotes = useCallback(async () => {
    if (!activeLesson || !user) return;
    try {
      const data = await api.get<Paginated<LessonNote> | LessonNote[]>(`/enrollments/lesson-notes/?course=${course.id}`);
      setNotes(unwrap(data));
      setNoteError("");
    } catch (error) {
      setNoteError(error instanceof ApiError ? error.message : "Impossible de charger vos notes.");
    }
  }, [activeLesson, user, course.id]);

  useEffect(() => { void loadNotes(); }, [loadNotes]);

  async function addNote() {
    if (!activeLesson || !noteDraft.trim() || noteBusy) return;
    setNoteBusy(true);
    setNoteError("");
    try {
      const created = await api.post<LessonNote>("/enrollments/lesson-notes/", {
        lesson: activeLesson.id,
        timestamp_seconds: Math.floor(currentTime),
        content: noteDraft.trim(),
      });
      setNotes((prev) => [...prev, created]);
      setNoteDraft("");
    } catch (error) {
      setNoteError(error instanceof ApiError ? error.message : "Impossible d'enregistrer cette note.");
    } finally {
      setNoteBusy(false);
    }
  }

  async function saveEditedNote(note: LessonNote) {
    if (!editingNoteText.trim()) return;
    setNoteBusy(true);
    try {
      const updated = await api.patch<LessonNote>(`/enrollments/lesson-notes/${note.id}/`, { content: editingNoteText.trim() });
      setNotes((prev) => prev.map((item) => item.id === note.id ? updated : item));
      setEditingNoteId(null);
      setEditingNoteText("");
    } catch (error) {
      setNoteError(error instanceof ApiError ? error.message : "Impossible de modifier cette note.");
    } finally {
      setNoteBusy(false);
    }
  }

  async function deleteNote(note: LessonNote) {
    if (!window.confirm("Supprimer cette note ?")) return;
    try {
      await api.del(`/enrollments/lesson-notes/${note.id}/`);
      setNotes((prev) => prev.filter((item) => item.id !== note.id));
    } catch (error) {
      setNoteError(error instanceof ApiError ? error.message : "Impossible de supprimer cette note.");
    }
  }

  function exportNotes() {
    if (!notes.length) return;
    const lines = notes.map((note) => `[${formatSeconds(note.timestamp_seconds)}] ${note.section_title} · ${note.lesson_title}\n${note.content}`).join("\n\n");
    const blob = new Blob([`${course.title}\n${"=".repeat(course.title.length)}\n\n${lines}\n`], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `notes-${course.slug}.txt`;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    URL.revokeObjectURL(url);
  }

  const loadComments = useCallback(async () => {
    if (!activeLesson || !user) return;
    try {
      const data = await api.get<Paginated<LessonComment> | LessonComment[]>(`/reviews/comments/?lesson=${activeLesson.id}&ordering=created_at`);
      setComments(unwrap(data));
      setQuestionError("");
    } catch (error) {
      setQuestionError(error instanceof ApiError ? error.message : "Impossible de charger les questions.");
    }
  }, [activeLesson, user]);

  useEffect(() => { if (tab === "qna") void loadComments(); }, [tab, loadComments]);

  useEffect(() => {
    if (tab !== "project" || !user || !course.is_enrolled) return;
    setProjectsLoading(true);
    api.get<ProjectAssignment[]>("/projects/assignments/")
      .then((rows) => setCourseProjects(rows.filter((row) => row.course === course.id)))
      .catch(() => setCourseProjects([]))
      .finally(() => setProjectsLoading(false));
  }, [tab, user, course.id, course.is_enrolled]);

  async function askQuestion() {
    if (!activeLesson || !questionDraft.trim() || questionBusy) return;
    setQuestionBusy(true);
    try {
      const created = await api.post<LessonComment>("/reviews/comments/", { lesson: activeLesson.id, content: questionDraft.trim() });
      setComments((prev) => [...prev, created]);
      setQuestionDraft("");
      setQuestionError("");
    } catch (error) {
      setQuestionError(error instanceof ApiError ? error.message : "Impossible d'envoyer votre question.");
    } finally {
      setQuestionBusy(false);
    }
  }

  const transcriptSegments = useMemo(() => {
    const lessons = transcriptScope === "video" ? (activeLesson ? [activeLesson] : []) : allLessons;
    const query = transcriptQuery.trim().toLocaleLowerCase("fr");
    return lessons
      .flatMap(parseTranscript)
      .filter((segment) => !query || segment.text.toLocaleLowerCase("fr").includes(query));
  }, [activeLesson, allLessons, transcriptQuery, transcriptScope]);

  function jumpToTranscript(segment: TranscriptSegment) {
    if (segment.lesson.locked) return;
    if (activeLesson?.id === segment.lesson.id) {
      if (segment.seconds != null) playerRef.current?.seekTo(segment.seconds);
    } else {
      selectLesson(segment.lesson, segment.seconds || 0);
    }
  }

  const displayedNotes = noteScope === "course" ? notes : notes.filter((note) => note.lesson === activeLesson?.id);

  function jumpToNote(note: LessonNote) {
    if (activeLesson?.id === note.lesson) {
      playerRef.current?.seekTo(note.timestamp_seconds);
      return;
    }
    const lesson = allLessons.find((item) => item.id === note.lesson);
    if (lesson && !lesson.locked) selectLesson(lesson, note.timestamp_seconds);
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

  const initialTime = activeLesson
    ? seekTarget?.lessonId === activeLesson.id
      ? seekTarget.seconds
      : resumePositions[activeLesson.id] || 0
    : 0;

  return (
    <div ref={mainRef} className="min-h-screen bg-[#f5f7f9] text-gray-950">
      {/* Workspace header, volontairement neutre : ergonomie type plateforme de formation sans copier le branding LinkedIn. */}
      <div className="sticky top-[72px] z-40 border-b border-white/10 bg-[#0b1728] text-white shadow-sm">
        <div className="flex h-14 items-center gap-2 px-3 sm:px-5">
          <Link href={`/courses/${course.slug}`} className="grid h-9 w-9 shrink-0 place-items-center rounded-lg text-white/80 hover:bg-white/10 hover:text-white" aria-label="Retour au cours">
            <ChevronLeft size={21} />
          </Link>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium text-white/60">{course.title}</p>
            <p className="truncate text-sm font-semibold">{activeLesson?.title || "Lecture du cours"}</p>
          </div>
          {enrollment && (
            <div className="hidden min-w-36 sm:block">
              <div className="mb-1 flex justify-between text-[10px] text-white/50"><span>Progression</span><span>{enrollment.progress_percent}%</span></div>
              <div className="h-1 overflow-hidden rounded-full bg-white/20"><div className="h-full rounded-full bg-emerald-400" style={{ width: `${enrollment.progress_percent}%` }} /></div>
            </div>
          )}
          <button
            type="button"
            onClick={() => setSidebarOpen((value) => !value)}
            className="hidden items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold text-white/75 hover:bg-white/10 hover:text-white lg:flex"
          >
            <BookOpen size={16} /> {sidebarOpen ? "Masquer le sommaire" : "Sommaire"}
          </button>
          <button type="button" onClick={() => setMobileSidebarOpen(true)} className="rounded-lg p-2 hover:bg-white/10 lg:hidden" aria-label="Ouvrir le sommaire"><Menu size={20} /></button>
        </div>
      </div>

      <div className="flex min-w-0">
        {sidebarOpen && (
          <aside className="sticky top-[7.5rem] hidden h-[calc(100vh-7.5rem)] w-[350px] shrink-0 flex-col border-r border-gray-200 bg-white lg:flex xl:w-[390px]">
            <CourseOutline
              course={course}
              enrollment={enrollment}
              activeLesson={activeLesson}
              completedIds={completedIds}
              openSections={openSections}
              setOpenSections={setOpenSections}
              onSelect={selectLesson}
            />
          </aside>
        )}

        <main className="min-w-0 flex-1">
          <section className="bg-[#07101d]">
            <div className="mx-auto w-full max-w-[1500px]">
              <div className="aspect-video w-full bg-black">
                {activeLesson?.video_url || activeLesson?.video_file ? (
                  <VideoPlayer
                    ref={playerRef}
                    key={activeLesson.id}
                    src={(activeLesson.video_url || activeLesson.video_file) as string}
                    hlsSrc={activeLesson.hls_url}
                    audioHlsSrc={activeLesson.audio_hls_url}
                    streamingVariants={activeLesson.streaming_variants}
                    streamingStatus={activeLesson.streaming_status}
                    poster={course.thumbnail}
                    title={activeLesson.title}
                    subtitlesUrl={activeLesson.subtitles_file}
                    initialTime={initialTime}
                    autoPlayOnLoad={autoStartLesson}
                    onTimeChange={(seconds, duration) => { setCurrentTime(seconds); setVideoDuration(duration); }}
                    onProgress={(seconds) => persistProgress(seconds)}
                    onEnded={() => void handleEnded()}
                    onRepair={canRepairActiveVideo ? repairActiveVideo : undefined}
                  />
                ) : (
                  <div className="grid h-full place-items-center text-center text-white/40">
                    <div><PlayCircle size={54} className="mx-auto" /><p className="mt-3 text-sm">Aucune vidéo pour cette leçon.</p></div>
                  </div>
                )}
              </div>
            </div>
          </section>

          <div className="border-b border-gray-200 bg-white">
            <div className="mx-auto flex max-w-[1500px] flex-wrap items-center gap-2 px-4 py-3 sm:px-6">
              <button
                type="button"
                disabled={!previousLesson || previousLesson.locked}
                onClick={() => previousLesson && selectLesson(previousLesson)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-35"
              >
                <ArrowLeft size={15} /> Précédente
              </button>
              <button
                type="button"
                disabled={!nextLesson || nextLesson.locked}
                onClick={() => nextLesson && selectLesson(nextLesson)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-2 text-xs font-semibold text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-35"
              >
                Suivante <ArrowRight size={15} />
              </button>
              <span className="hidden text-xs text-gray-400 sm:inline">
                {currentIndex + 1} / {allLessons.length} · {formatSeconds(currentTime)}{videoDuration > 0 ? ` / ${formatSeconds(videoDuration)}` : ""}
              </span>
              <span className="flex-1" />
              <label className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50">
                <button
                  type="button"
                  role="switch"
                  aria-checked={autoplay}
                  onClick={() => setAutoplay((value) => !value)}
                  className={`relative h-5 w-9 rounded-full transition ${autoplay ? "bg-emerald-600" : "bg-gray-300"}`}
                >
                  <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-white shadow transition ${autoplay ? "left-[18px]" : "left-0.5"}`} />
                </button>
                Lecture automatique
              </label>
              {activeLesson && (
                <button
                  type="button"
                  onClick={() => void markComplete(activeLesson)}
                  className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-xs font-semibold ${completedIds.has(activeLesson.id) ? "bg-emerald-50 text-emerald-700" : "border border-gray-200 text-gray-700 hover:bg-gray-50"}`}
                >
                  <CheckCircle2 size={15} /> {completedIds.has(activeLesson.id) ? "Terminée" : "Marquer comme terminée"}
                </button>
              )}
            </div>
          </div>

          <section className="mx-auto max-w-[1500px] px-4 py-5 sm:px-6 sm:py-7">
            <div className="mb-5">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-emerald-700">{currentIndex >= 0 ? `Leçon ${currentIndex + 1}` : "Cours"}</p>
              <h1 className="mt-1 text-xl font-bold tracking-tight sm:text-2xl">{activeLesson?.title || course.title}</h1>
            </div>

            <div className="overflow-x-auto border-b border-gray-200">
              <div className="flex min-w-max gap-1">
                {([
                  ["overview", "Aperçu"],
                  ["transcript", "Transcription"],
                  ["notes", "Carnet"],
                  ["qna", "Q&R"],
                  ["resources", "Ressources"],
                  ["project", "Projet"],
                ] as [LearningTab, string][]).map(([value, label]) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setTab(value)}
                    className={`border-b-2 px-4 py-3 text-sm font-semibold transition ${tab === value ? "border-emerald-600 text-emerald-700" : "border-transparent text-gray-500 hover:text-gray-900"}`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>

            <div className="py-6">
              {tab === "overview" && (
                <OverviewPanel course={course} lesson={activeLesson} />
              )}

              {tab === "transcript" && (
                <TranscriptPanel
                  segments={transcriptSegments}
                  query={transcriptQuery}
                  setQuery={setTranscriptQuery}
                  scope={transcriptScope}
                  setScope={setTranscriptScope}
                  activeLesson={activeLesson}
                  onJump={jumpToTranscript}
                />
              )}

              {tab === "notes" && (
                <NotesPanel
                  currentTime={currentTime}
                  notes={displayedNotes}
                  totalNotes={notes.length}
                  scope={noteScope}
                  setScope={setNoteScope}
                  noteDraft={noteDraft}
                  setNoteDraft={setNoteDraft}
                  noteBusy={noteBusy}
                  noteError={noteError}
                  editingNoteId={editingNoteId}
                  editingNoteText={editingNoteText}
                  setEditingNoteId={setEditingNoteId}
                  setEditingNoteText={setEditingNoteText}
                  onAdd={() => void addNote()}
                  onSave={(note) => void saveEditedNote(note)}
                  onDelete={(note) => void deleteNote(note)}
                  onJump={jumpToNote}
                  onExport={exportNotes}
                />
              )}

              {tab === "qna" && (
                <QnaPanel
                  comments={comments}
                  draft={questionDraft}
                  setDraft={setQuestionDraft}
                  busy={questionBusy}
                  error={questionError}
                  onSubmit={() => void askQuestion()}
                />
              )}

              {tab === "resources" && <ResourcesPanel course={course} />}
              {tab === "project" && <ProjectPanel course={course} projects={courseProjects} loading={projectsLoading} />}
            </div>
          </section>
        </main>
      </div>

      {mobileSidebarOpen && (
        <div className="fixed inset-0 z-[80] lg:hidden">
          <button className="absolute inset-0 bg-black/60" onClick={() => setMobileSidebarOpen(false)} aria-label="Fermer le sommaire" />
          <aside className="absolute inset-y-0 left-0 flex w-[88vw] max-w-sm flex-col bg-white shadow-2xl">
            <div className="flex h-14 items-center justify-between border-b border-gray-200 px-4">
              <p className="font-bold">Contenu du cours</p>
              <button onClick={() => setMobileSidebarOpen(false)} className="rounded-lg p-2 hover:bg-gray-100"><X size={19} /></button>
            </div>
            <CourseOutline
              course={course}
              enrollment={enrollment}
              activeLesson={activeLesson}
              completedIds={completedIds}
              openSections={openSections}
              setOpenSections={setOpenSections}
              onSelect={selectLesson}
            />
          </aside>
        </div>
      )}
    </div>
  );
}

function CourseOutline({
  course,
  enrollment,
  activeLesson,
  completedIds,
  openSections,
  setOpenSections,
  onSelect,
}: {
  course: Course;
  enrollment: CourseEnrollment | null;
  activeLesson: Lesson | null;
  completedIds: Set<number>;
  openSections: Set<number>;
  setOpenSections: Dispatch<SetStateAction<Set<number>>>;
  onSelect: (lesson: Lesson) => void;
}) {
  const totalLessons = (course.sections || []).reduce((sum, section) => sum + section.lessons.length, 0);
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="border-b border-gray-200 px-4 py-4">
        <div className="flex items-center justify-between gap-3">
          <div><p className="text-sm font-bold">Contenu du cours</p><p className="mt-0.5 text-xs text-gray-400">{totalLessons} leçon(s) · {formatDuration(course.total_duration_minutes)}</p></div>
          {enrollment && <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-bold text-emerald-700">{enrollment.progress_percent}%</span>}
        </div>
        {enrollment && <div className="mt-3"><ProgressBar value={enrollment.progress_percent} /></div>}
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        {(course.sections || []).map((section: Section, sectionIndex) => {
          const open = openSections.has(section.id);
          const sectionDone = section.lessons.filter((lesson) => completedIds.has(lesson.id)).length;
          return (
            <div key={section.id} className="border-b border-gray-100">
              <button
                type="button"
                onClick={() => setOpenSections((prev) => {
                  const next = new Set(prev);
                  if (next.has(section.id)) next.delete(section.id); else next.add(section.id);
                  return next;
                })}
                className="flex w-full items-start gap-3 bg-gray-50/70 px-4 py-3 text-left hover:bg-gray-100"
              >
                <ChevronDown size={16} className={`mt-0.5 shrink-0 text-gray-400 transition ${open ? "rotate-0" : "-rotate-90"}`} />
                <span className="min-w-0 flex-1"><span className="block text-xs font-bold text-gray-900">{sectionIndex + 1}. {section.title}</span><span className="mt-1 block text-[11px] text-gray-400">{sectionDone}/{section.lessons.length} · {formatDuration(section.duration_minutes)}</span></span>
              </button>
              {open && section.lessons.map((lesson, lessonIndex) => {
                const active = activeLesson?.id === lesson.id;
                const done = completedIds.has(lesson.id);
                return (
                  <button
                    type="button"
                    key={lesson.id}
                    disabled={lesson.locked}
                    onClick={() => onSelect(lesson)}
                    className={`flex w-full items-start gap-3 border-l-4 px-4 py-3 text-left transition ${active ? "border-emerald-600 bg-emerald-50/70" : "border-transparent hover:bg-gray-50"} disabled:cursor-not-allowed disabled:opacity-55`}
                  >
                    <span className="mt-0.5 shrink-0">{lesson.locked ? <Lock size={15} className="text-gray-400" /> : done ? <CheckCircle2 size={16} className="text-emerald-600" /> : <Circle size={16} className="text-gray-300" />}</span>
                    <span className="min-w-0 flex-1">
                      <span className={`block text-xs leading-5 ${active ? "font-bold text-emerald-900" : "font-medium text-gray-700"}`}>{lessonIndex + 1}. {lesson.title}</span>
                      <span className="mt-1 flex items-center gap-1 text-[11px] text-gray-400"><Clock size={11} /> {formatDuration(lesson.duration_minutes)}{lesson.is_preview ? " · Aperçu" : ""}</span>
                    </span>
                    {active && <ChevronRight size={14} className="mt-1 shrink-0 text-emerald-600" />}
                  </button>
                );
              })}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function OverviewPanel({ course, lesson }: { course: Course; lesson: Lesson | null }) {
  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_320px]">
      <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm sm:p-6">
        <h2 className="text-base font-bold">À propos de cette leçon</h2>
        <p className="mt-3 whitespace-pre-wrap text-sm leading-7 text-gray-600">{lesson?.description || "Cette leçon ne contient pas encore de description."}</p>
      </div>
      <div className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">Cours</p>
        <p className="mt-2 font-bold">{course.title}</p>
        <div className="mt-4 space-y-2 text-sm text-gray-600">
          <p><span className="font-medium text-gray-900">Formateur :</span> {course.instructor.full_name}</p>
          <p><span className="font-medium text-gray-900">Durée :</span> {formatDuration(course.total_duration_minutes)}</p>
          <p><span className="font-medium text-gray-900">Leçons :</span> {course.total_lessons}</p>
          <p><span className="font-medium text-gray-900">Langue :</span> {course.language}</p>
        </div>
      </div>
    </div>
  );
}

function ProjectPanel({ course, projects, loading }: { course: Course; projects: ProjectAssignment[]; loading: boolean }) {
  if (!course.is_enrolled) return <div className="rounded-2xl border border-gray-200 bg-white p-8 text-center text-sm text-gray-500">Inscrivez-vous au cours pour accéder aux projets pratiques.</div>;
  return (
    <div className="rounded-2xl border border-gray-200 bg-white shadow-sm">
      <div className="border-b border-gray-100 p-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div><h2 className="flex items-center gap-2 font-bold"><BriefcaseBusiness size={18} className="text-emerald-700"/>Projets pratiques</h2><p className="mt-1 text-xs text-gray-400">Appliquez le cours sur un livrable concret et obtenez une validation de votre instructeur.</p></div>
          <Link href="/dashboard/student/projects" className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-700">Ouvrir mes projets</Link>
        </div>
      </div>
      <div className="p-5">
        {loading ? <p className="text-sm text-gray-400">Chargement...</p> : projects.length === 0 ? <p className="text-sm text-gray-500">Aucun projet n'est encore associé à ce cours.</p> : <div className="space-y-3">
          {projects.map((project) => <div key={project.id} className="rounded-xl border border-gray-100 bg-gray-50 p-4"><div className="flex flex-wrap items-start justify-between gap-2"><div><p className="font-semibold">{project.title}</p><p className="mt-1 line-clamp-2 text-xs leading-5 text-gray-500">{project.brief}</p></div>{project.required_for_certificate && <span className="rounded-full bg-violet-50 px-2 py-1 text-[10px] font-bold text-violet-700">Requis pour certificat</span>}</div><div className="mt-3 flex items-center justify-between gap-3 text-[11px] text-gray-400"><span>Validation {project.passing_score}/{project.max_score}</span><span className="font-semibold text-emerald-700">{project.submission?.status === "approved" ? "Validé" : project.submission ? "En cours" : "À faire"}</span></div></div>)}
        </div>}
      </div>
    </div>
  );
}

function TranscriptPanel({
  segments,
  query,
  setQuery,
  scope,
  setScope,
  activeLesson,
  onJump,
}: {
  segments: TranscriptSegment[];
  query: string;
  setQuery: (value: string) => void;
  scope: TranscriptScope;
  setScope: (value: TranscriptScope) => void;
  activeLesson: Lesson | null;
  onJump: (segment: TranscriptSegment) => void;
}) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white shadow-sm">
      <div className="border-b border-gray-100 p-4 sm:p-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Rechercher dans la transcription…" className="w-full rounded-xl border border-gray-200 py-2.5 pl-9 pr-3 text-sm outline-none transition focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100" />
          </div>
          <div className="flex rounded-xl bg-gray-100 p-1 text-xs font-semibold">
            <button type="button" onClick={() => setScope("video")} className={`rounded-lg px-3 py-2 ${scope === "video" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"}`}>Cette vidéo</button>
            <button type="button" onClick={() => setScope("course")} className={`rounded-lg px-3 py-2 ${scope === "course" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"}`}>Tout le cours</button>
          </div>
        </div>
      </div>
      <div className="max-h-[560px] overflow-y-auto p-3 sm:p-4">
        {!segments.length ? (
          <div className="py-14 text-center"><FileText size={30} className="mx-auto text-gray-300" /><p className="mt-3 text-sm font-medium text-gray-500">{activeLesson?.transcript ? "Aucun résultat." : "Aucune transcription disponible pour cette leçon."}</p></div>
        ) : (
          <div className="space-y-1">
            {segments.map((segment, index) => (
              <button
                key={`${segment.lesson.id}-${segment.seconds ?? "p"}-${index}`}
                type="button"
                onClick={() => onJump(segment)}
                className="group flex w-full gap-3 rounded-xl px-3 py-3 text-left hover:bg-gray-50"
              >
                <span className={`mt-0.5 min-w-12 text-xs font-bold ${segment.seconds != null ? "text-emerald-700" : "text-gray-300"}`}>{segment.seconds != null ? formatSeconds(segment.seconds) : "—"}</span>
                <span className="min-w-0 flex-1"><span className="text-sm leading-6 text-gray-700">{segment.text}</span>{scope === "course" && <span className="mt-1 block text-[11px] font-medium text-gray-400">{segment.lesson.title}</span>}</span>
              </button>
            ))}
          </div>
        )}
      </div>
      <div className="border-t border-gray-100 px-5 py-3 text-[11px] text-gray-400">Les lignes préfixées par [mm:ss] ou [hh:mm:ss] deviennent cliquables et permettent d'aller directement au passage correspondant.</div>
    </div>
  );
}

function NotesPanel({
  currentTime,
  notes,
  totalNotes,
  scope,
  setScope,
  noteDraft,
  setNoteDraft,
  noteBusy,
  noteError,
  editingNoteId,
  editingNoteText,
  setEditingNoteId,
  setEditingNoteText,
  onAdd,
  onSave,
  onDelete,
  onJump,
  onExport,
}: {
  currentTime: number;
  notes: LessonNote[];
  totalNotes: number;
  scope: "lesson" | "course";
  setScope: (value: "lesson" | "course") => void;
  noteDraft: string;
  setNoteDraft: (value: string) => void;
  noteBusy: boolean;
  noteError: string;
  editingNoteId: number | null;
  editingNoteText: string;
  setEditingNoteId: (value: number | null) => void;
  setEditingNoteText: (value: string) => void;
  onAdd: () => void;
  onSave: (note: LessonNote) => void;
  onDelete: (note: LessonNote) => void;
  onJump: (note: LessonNote) => void;
  onExport: () => void;
}) {
  return (
    <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_320px]">
      <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm sm:p-5">
        <div className="mb-3 flex items-center justify-between gap-3"><div><h2 className="font-bold">Mon carnet</h2><p className="mt-1 text-xs text-gray-400">La note sera liée à {formatSeconds(currentTime)} dans la vidéo.</p></div><button type="button" onClick={onExport} disabled={!totalNotes} className="inline-flex items-center gap-1.5 rounded-lg border border-gray-200 px-3 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-50 disabled:opacity-35"><Download size={14} /> Exporter</button></div>
        <textarea value={noteDraft} onChange={(event) => setNoteDraft(event.target.value)} onKeyDown={(event) => { if ((event.ctrlKey || event.metaKey) && event.key === "Enter") onAdd(); }} placeholder="Saisissez une note personnelle…" className="min-h-28 w-full resize-y rounded-xl border border-gray-200 p-3 text-sm leading-6 outline-none transition focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100" />
        <div className="mt-3 flex items-center justify-between gap-3"><p className="text-[11px] text-gray-400">Ctrl/⌘ + Entrée pour enregistrer</p><button type="button" onClick={onAdd} disabled={!noteDraft.trim() || noteBusy} className="rounded-lg bg-emerald-600 px-4 py-2 text-xs font-bold text-white hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-40">Ajouter la note</button></div>
        {noteError && <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">{noteError}</p>}
      </div>
      <div className="rounded-2xl border border-gray-200 bg-white shadow-sm lg:row-span-2">
        <div className="border-b border-gray-100 px-4 py-3">
          <div className="flex items-center justify-between gap-2"><div><p className="text-sm font-bold">Mes notes</p><p className="mt-0.5 text-[11px] text-gray-400">{notes.length} affichée(s) · {totalNotes} dans le cours</p></div></div>
          <div className="mt-3 flex rounded-lg bg-gray-100 p-1 text-[11px] font-semibold"><button type="button" onClick={() => setScope("lesson")} className={`flex-1 rounded-md px-2 py-1.5 ${scope === "lesson" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"}`}>Cette leçon</button><button type="button" onClick={() => setScope("course")} className={`flex-1 rounded-md px-2 py-1.5 ${scope === "course" ? "bg-white text-gray-900 shadow-sm" : "text-gray-500"}`}>Tout le cours</button></div>
        </div>
        <div className="max-h-[520px] overflow-y-auto p-3">
          {!notes.length ? <p className="py-10 text-center text-sm text-gray-400">Aucune note pour le moment.</p> : notes.map((note) => (
            <div key={note.id} className="group mb-2 rounded-xl border border-gray-100 p-3 last:mb-0 hover:border-gray-200">
              <div className="mb-2 flex items-center justify-between gap-2">
                <button type="button" onClick={() => onJump(note)} className="rounded-md bg-emerald-50 px-2 py-1 text-[11px] font-bold text-emerald-700 hover:bg-emerald-100">{formatSeconds(note.timestamp_seconds)}</button>
                <div className="flex opacity-100 sm:opacity-0 sm:group-hover:opacity-100">
                  <button type="button" onClick={() => { setEditingNoteId(note.id); setEditingNoteText(note.content); }} className="rounded-md p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700" aria-label="Modifier"><Edit3 size={13} /></button>
                  <button type="button" onClick={() => onDelete(note)} className="rounded-md p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600" aria-label="Supprimer"><Trash2 size={13} /></button>
                </div>
              </div>
              {scope === "course" && <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-wide text-gray-400">{note.section_title} · {note.lesson_title}</p>}
              {editingNoteId === note.id ? <div><textarea value={editingNoteText} onChange={(event) => setEditingNoteText(event.target.value)} className="min-h-20 w-full rounded-lg border border-gray-200 p-2 text-xs outline-none focus:border-emerald-400" /><div className="mt-2 flex justify-end gap-2"><button onClick={() => setEditingNoteId(null)} className="px-2 py-1 text-[11px] font-semibold text-gray-500">Annuler</button><button onClick={() => onSave(note)} className="rounded-md bg-emerald-600 px-2.5 py-1.5 text-[11px] font-bold text-white">Enregistrer</button></div></div> : <p className="whitespace-pre-wrap text-xs leading-5 text-gray-700">{note.content}</p>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function QnaPanel({ comments, draft, setDraft, busy, error, onSubmit }: { comments: LessonComment[]; draft: string; setDraft: (value: string) => void; busy: boolean; error: string; onSubmit: () => void }) {
  return (
    <div className="rounded-2xl border border-gray-200 bg-white shadow-sm">
      <div className="border-b border-gray-100 p-4 sm:p-5">
        <h2 className="font-bold">Questions et réponses</h2>
        <p className="mt-1 text-xs text-gray-400">Posez une question sur cette leçon. L'instructeur pourra vous répondre depuis son tableau de bord.</p>
        <div className="mt-4 flex gap-2"><textarea value={draft} onChange={(event) => setDraft(event.target.value)} placeholder="Votre question…" className="min-h-20 min-w-0 flex-1 rounded-xl border border-gray-200 p-3 text-sm outline-none focus:border-emerald-400 focus:ring-2 focus:ring-emerald-100" /><button type="button" onClick={onSubmit} disabled={!draft.trim() || busy} className="self-end rounded-xl bg-emerald-600 p-3 text-white hover:bg-emerald-700 disabled:opacity-40" aria-label="Envoyer"><Send size={18} /></button></div>
        {error && <p className="mt-3 rounded-lg bg-red-50 px-3 py-2 text-xs text-red-700">{error}</p>}
      </div>
      <div className="divide-y divide-gray-100">
        {!comments.length ? <div className="py-14 text-center"><MessageSquare size={30} className="mx-auto text-gray-300" /><p className="mt-3 text-sm text-gray-400">Aucune question pour cette leçon.</p></div> : comments.map((comment) => (
          <div key={comment.id} className="p-4 sm:p-5">
            <div className="flex items-center justify-between gap-3"><p className="text-sm font-bold">{comment.user?.full_name || "Apprenant"}</p><p className="text-[11px] text-gray-400">{new Date(comment.created_at).toLocaleString("fr-FR")}</p></div>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-gray-700">{comment.content}</p>
            {!!comment.replies?.length && <div className="mt-4 space-y-3 border-l-2 border-emerald-100 pl-4">{comment.replies.map((reply) => <div key={reply.id}><div className="flex items-center gap-2"><p className="text-xs font-bold text-emerald-800">{reply.user?.full_name || "Instructeur"}</p><span className="text-[10px] text-gray-400">{new Date(reply.created_at).toLocaleDateString("fr-FR")}</span></div><p className="mt-1 text-xs leading-5 text-gray-600">{reply.content}</p></div>)}</div>}
          </div>
        ))}
      </div>
    </div>
  );
}

function ResourcesPanel({ course }: { course: Course }) {
  const resources = course.pdf_resources || [];
  return (
    <div className="rounded-2xl border border-gray-200 bg-white shadow-sm">
      <div className="border-b border-gray-100 px-5 py-4"><h2 className="font-bold">Ressources du cours</h2><p className="mt-1 text-xs text-gray-400">Documents fournis par l'instructeur pour accompagner la formation.</p></div>
      <div className="p-4">
        {!resources.length ? <p className="py-10 text-center text-sm text-gray-400">Aucune ressource pour ce cours.</p> : <div className="grid gap-2">{resources.map((pdf) => (
          <div key={pdf.id} className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-gray-100 px-4 py-3 hover:bg-gray-50">
            <div className="flex min-w-0 items-center gap-3"><div className="grid h-10 w-10 shrink-0 place-items-center rounded-lg bg-amber-50 text-amber-700"><FileText size={18} /></div><div className="min-w-0"><p className="truncate text-sm font-semibold">{pdf.title}</p><p className="mt-0.5 text-[11px] text-gray-400">{pdf.page_count} page(s){pdf.is_free_sample ? " · extrait gratuit" : ""}</p></div></div>
            {pdf.file && !pdf.locked ? <PdfViewer url={pdf.file} title={pdf.title} /> : <span className="text-xs text-gray-400">Verrouillé</span>}
          </div>
        ))}</div>}
      </div>
    </div>
  );
}
