"use client";

import { useEffect, useState, useCallback } from "react";
import { PlusCircle, Trash2, PlayCircle, FileText, Eye, EyeOff, Loader2 } from "lucide-react";
import { api } from "@/lib/api";
import { Course } from "@/types";
import DashboardNav from "@/components/dashboard/DashboardNav";

export default function ManageCoursePage({ params }: { params: { id: string } }) {
  const [course, setCourse] = useState<Course | null>(null);
  const [loading, setLoading] = useState(true);
  const [newSectionTitle, setNewSectionTitle] = useState("");
  const [publishing, setPublishing] = useState(false);

  const load = useCallback(async () => {
    // On récupère via l'endpoint public par id: on liste puis filtre (simplification MVP)
    const list = await api.get<{ results: Course[] } | Course[]>("/catalog/courses/my_courses/");
    const arr: Course[] = (list as any).results || (list as any);
    const found = arr.find((c) => c.id === Number(params.id));
    if (found) {
      const detail = await api.get<Course>(`/catalog/courses/${found.slug}/`);
      setCourse(detail);
    }
    setLoading(false);
  }, [params.id]);

  useEffect(() => { load(); }, [load]);

  async function addSection() {
    if (!newSectionTitle.trim() || !course) return;
    await api.post("/catalog/sections/", { course: course.id, title: newSectionTitle, order: (course.sections?.length || 0) + 1 });
    setNewSectionTitle("");
    load();
  }

  async function addLesson(sectionId: number, title: string, duration: number, videoUrl: string) {
    await api.post("/catalog/lessons/", {
      section: sectionId, title, duration_minutes: duration, video_url: videoUrl, order: 1,
    });
    load();
  }

  async function addPdf(title: string, pageCount: number) {
    if (!course) return;
    // NOTE: upload de fichier réel via FormData à brancher côté production.
    await api.post("/catalog/pdf-resources/", { course: course.id, title, page_count: pageCount, order: 1 });
    load();
  }

  async function togglePublish() {
    if (!course) return;
    setPublishing(true);
    try {
      await api.patch(`/catalog/courses/${course.slug}/`, { published: !course.published });
      load();
    } finally {
      setPublishing(false);
    }
  }

  if (loading) return <div className="container-app py-20 text-center text-gray-500"><Loader2 className="mx-auto animate-spin" /></div>;
  if (!course) return <div className="container-app py-20 text-center text-gray-500">Cours introuvable.</div>;

  return (
    <div className="container-app py-10">
      <DashboardNav role="instructor" />

      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold">{course.title}</h1>
          <p className="text-sm text-gray-500">
            {course.total_lessons} vidéos · {course.total_hours} h · {course.pdf_resources?.length || 0} PDF
          </p>
        </div>
        <button onClick={togglePublish} disabled={publishing} className={course.published ? "btn-outline" : "btn-primary"}>
          {course.published ? <EyeOff size={16} /> : <Eye size={16} />}
          {course.published ? "Dépublier" : "Publier le cours"}
        </button>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_340px]">
        <div className="flex flex-col gap-6">
          {(course.sections || []).map((section) => (
            <div key={section.id} className="card p-5">
              <h3 className="mb-3 font-bold">{section.title}</h3>
              <div className="flex flex-col gap-2">
                {section.lessons.map((lesson) => (
                  <div key={lesson.id} className="flex items-center gap-2 rounded-lg border border-gray-100 px-3 py-2 text-sm">
                    <PlayCircle size={16} className="text-brand-600" />
                    <span className="flex-1">{lesson.title}</span>
                    <span className="text-xs text-gray-400">{lesson.duration_minutes} min</span>
                  </div>
                ))}
              </div>
              <AddLessonForm onAdd={(title, duration, url) => addLesson(section.id, title, duration, url)} />
            </div>
          ))}

          <div className="card flex items-center gap-2 p-4">
            <input
              value={newSectionTitle}
              onChange={(e) => setNewSectionTitle(e.target.value)}
              placeholder="Titre de la nouvelle section (ex: Introduction)"
              className="flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm"
            />
            <button onClick={addSection} className="btn-primary !py-2 !text-sm"><PlusCircle size={16} /> Ajouter</button>
          </div>
        </div>

        <div>
          <div className="card p-5">
            <h3 className="mb-3 flex items-center gap-2 font-bold"><FileText size={18} className="text-amber-600" /> PDF du cours</h3>
            <div className="flex flex-col gap-2">
              {(course.pdf_resources || []).map((pdf) => (
                <div key={pdf.id} className="flex items-center gap-2 rounded-lg border border-gray-100 px-3 py-2 text-sm">
                  <FileText size={14} className="text-amber-600" />
                  <span className="flex-1 line-clamp-1">{pdf.title}</span>
                </div>
              ))}
            </div>
            <AddPdfForm onAdd={addPdf} />
          </div>
        </div>
      </div>
    </div>
  );
}

function AddLessonForm({ onAdd }: { onAdd: (title: string, duration: number, url: string) => void }) {
  const [title, setTitle] = useState("");
  const [duration, setDuration] = useState("10");
  const [url, setUrl] = useState("");

  return (
    <div className="mt-3 flex flex-col gap-2 border-t border-gray-100 pt-3">
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_100px]">
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Titre de la vidéo"
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm" />
        <input value={duration} onChange={(e) => setDuration(e.target.value)} type="number" placeholder="Min"
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm" />
      </div>
      <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="URL vidéo (mp4, YouTube non-listé...)"
        className="rounded-lg border border-gray-200 px-3 py-2 text-sm" />
      <button
        onClick={() => { if (title) { onAdd(title, Number(duration) || 0, url); setTitle(""); setUrl(""); } }}
        className="btn-outline !py-1.5 !text-xs self-start"
      >
        <PlusCircle size={14} /> Ajouter la vidéo
      </button>
    </div>
  );
}

function AddPdfForm({ onAdd }: { onAdd: (title: string, pageCount: number) => void }) {
  const [title, setTitle] = useState("");
  const [pages, setPages] = useState("10");

  return (
    <div className="mt-3 flex flex-col gap-2 border-t border-gray-100 pt-3">
      <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Titre du PDF"
        className="rounded-lg border border-gray-200 px-3 py-2 text-sm" />
      <input value={pages} onChange={(e) => setPages(e.target.value)} type="number" placeholder="Nombre de pages"
        className="rounded-lg border border-gray-200 px-3 py-2 text-sm" />
      <button
        onClick={() => { if (title) { onAdd(title, Number(pages) || 0); setTitle(""); } }}
        className="btn-outline !py-1.5 !text-xs self-start"
      >
        <PlusCircle size={14} /> Ajouter le PDF
      </button>
      <p className="text-xs text-gray-400">L'upload de fichier PDF/vidéo réel se fait via l'admin Django ou l'API multipart en production.</p>
    </div>
  );
}
