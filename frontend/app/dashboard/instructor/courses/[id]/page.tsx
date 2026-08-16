"use client";

import { useEffect, useState, useCallback } from "react";
import { PlusCircle, Trash2, PlayCircle, FileText, Eye, EyeOff, Loader2, Upload, Link as LinkIcon } from "lucide-react";
import { api } from "@/lib/api";
import { Course } from "@/types";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import DashboardNav from "@/components/dashboard/DashboardNav";
import GuardScreen from "@/components/ui/GuardScreen";

export default function ManageCoursePage({ params }: { params: { id: string } }) {
  const { ready } = useAuthGuard({ roles: ["instructor", "admin"], redirectTo: "/dashboard/instructor" });
  const [course, setCourse] = useState<Course | null>(null);
  const [loading, setLoading] = useState(true);
  const [newSectionTitle, setNewSectionTitle] = useState("");
  const [publishing, setPublishing] = useState(false);

  const load = useCallback(async () => {
    const list = await api.get<{ results: Course[] } | Course[]>("/catalog/courses/my_courses/");
    const arr: Course[] = (list as any).results || (list as any);
    const found = arr.find((c) => c.id === Number(params.id));
    if (found) {
      const detail = await api.get<Course>(`/catalog/courses/${found.slug}/`);
      setCourse(detail);
    }
    setLoading(false);
  }, [params.id]);

  useEffect(() => { if (ready) load(); }, [ready, load]);

  async function addSection() {
    if (!newSectionTitle.trim() || !course) return;
    await api.post("/catalog/sections/", { course: course.id, title: newSectionTitle, order: (course.sections?.length || 0) + 1 });
    setNewSectionTitle("");
    load();
  }

  async function deleteSection(sectionId: number) {
    if (!confirm("Supprimer cette section et toutes ses vidéos ?")) return;
    await api.del(`/catalog/sections/${sectionId}/`);
    load();
  }

  async function deleteLesson(lessonId: number) {
    if (!confirm("Supprimer cette vidéo ?")) return;
    await api.del(`/catalog/lessons/${lessonId}/`);
    load();
  }

  async function addLessonByUrl(sectionId: number, title: string, duration: number, videoUrl: string, isPreview: boolean) {
    await api.post("/catalog/lessons/", {
      section: sectionId, title, duration_minutes: duration, video_url: videoUrl,
      order: 1, is_preview: isPreview,
    });
    load();
  }

  async function addLessonByFile(sectionId: number, title: string, duration: number, file: File, isPreview: boolean) {
    const fd = new FormData();
    fd.append("section", String(sectionId));
    fd.append("title", title);
    fd.append("duration_minutes", String(duration));
    fd.append("order", "1");
    fd.append("is_preview", String(isPreview));
    fd.append("video_file", file);
    await api.post("/catalog/lessons/", fd);
    load();
  }

  async function addPdf(title: string, pageCount: number, file: File | null, isFreeSample: boolean) {
    if (!course) return;
    if (file) {
      const fd = new FormData();
      fd.append("course", String(course.id));
      fd.append("title", title);
      fd.append("page_count", String(pageCount));
      fd.append("is_free_sample", String(isFreeSample));
      fd.append("order", "1");
      fd.append("file", file);
      await api.post("/catalog/pdf-resources/", fd);
    } else {
      await api.post("/catalog/pdf-resources/", {
        course: course.id, title, page_count: pageCount, is_free_sample: isFreeSample, order: 1,
      });
    }
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

  if (!ready) return <GuardScreen />;
  if (loading) return <div className="container-app py-20 text-center text-gray-500"><Loader2 className="mx-auto animate-spin" /></div>;
  if (!course) return <div className="container-app py-20 text-center text-gray-500">Cours introuvable.</div>;

  const canPublish = (course.sections?.length || 0) > 0 && course.total_lessons > 0;

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
        <div className="flex items-center gap-2">
          {!canPublish && !course.published && (
            <span className="text-xs text-amber-600">Ajoutez au moins une vidéo avant de publier</span>
          )}
          <button onClick={togglePublish} disabled={publishing || (!canPublish && !course.published)}
            className={course.published ? "btn-outline" : "btn-primary disabled:cursor-not-allowed disabled:opacity-50"}>
            {course.published ? <EyeOff size={16} /> : <Eye size={16} />}
            {course.published ? "Dépublier" : "Publier le cours"}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[1fr_340px]">
        <div className="flex flex-col gap-6">
          {(course.sections || []).map((section) => (
            <div key={section.id} className="card p-5">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="font-bold">{section.title}</h3>
                <button onClick={() => deleteSection(section.id)} className="text-gray-400 hover:text-red-600">
                  <Trash2 size={16} />
                </button>
              </div>
              <div className="flex flex-col gap-2">
                {section.lessons.map((lesson) => (
                  <div key={lesson.id} className="flex items-center gap-2 rounded-lg border border-gray-100 px-3 py-2 text-sm">
                    <PlayCircle size={16} className="text-brand-600" />
                    <span className="flex-1">{lesson.title}</span>
                    {lesson.is_preview && <span className="badge bg-brand-50 text-brand-700">Aperçu gratuit</span>}
                    <span className="text-xs text-gray-400">{lesson.duration_minutes} min</span>
                    <button onClick={() => deleteLesson(lesson.id)} className="text-gray-400 hover:text-red-600">
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
              <AddLessonForm
                onAddUrl={(title, duration, url, preview) => addLessonByUrl(section.id, title, duration, url, preview)}
                onAddFile={(title, duration, file, preview) => addLessonByFile(section.id, title, duration, file, preview)}
              />
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
                  {pdf.is_free_sample && <span className="badge bg-brand-50 text-brand-700">Extrait</span>}
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

function AddLessonForm({
  onAddUrl, onAddFile,
}: {
  onAddUrl: (title: string, duration: number, url: string, preview: boolean) => void;
  onAddFile: (title: string, duration: number, file: File, preview: boolean) => void;
}) {
  const [mode, setMode] = useState<"file" | "url">("file");
  const [title, setTitle] = useState("");
  const [duration, setDuration] = useState("10");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState(false);
  const [uploading, setUploading] = useState(false);

  async function handleAdd() {
    if (!title) return;
    setUploading(true);
    try {
      if (mode === "file" && file) {
        await onAddFile(title, Number(duration) || 0, file, preview);
      } else if (mode === "url" && url) {
        await onAddUrl(title, Number(duration) || 0, url, preview);
      } else {
        return;
      }
      setTitle(""); setUrl(""); setFile(null); setPreview(false);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="mt-3 flex flex-col gap-2 border-t border-gray-100 pt-3">
      <div className="flex gap-2 text-xs">
        <button type="button" onClick={() => setMode("file")}
          className={`rounded-lg px-3 py-1.5 font-semibold ${mode === "file" ? "bg-brand-50 text-brand-700" : "bg-gray-100 text-gray-500"}`}>
          <Upload size={12} className="mr-1 inline" /> Uploader un fichier
        </button>
        <button type="button" onClick={() => setMode("url")}
          className={`rounded-lg px-3 py-1.5 font-semibold ${mode === "url" ? "bg-brand-50 text-brand-700" : "bg-gray-100 text-gray-500"}`}>
          <LinkIcon size={12} className="mr-1 inline" /> Lien externe
        </button>
      </div>

      <div className="grid grid-cols-1 gap-2 sm:grid-cols-[1fr_100px]">
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Titre de la vidéo"
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm" />
        <input value={duration} onChange={(e) => setDuration(e.target.value)} type="number" placeholder="Min"
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm" />
      </div>

      {mode === "file" ? (
        <input type="file" accept="video/*" onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="rounded-lg border border-dashed border-gray-300 px-3 py-2 text-sm" />
      ) : (
        <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://... (mp4 ou flux vidéo)"
          className="rounded-lg border border-gray-200 px-3 py-2 text-sm" />
      )}

      <label className="flex items-center gap-2 text-xs text-gray-600">
        <input type="checkbox" checked={preview} onChange={(e) => setPreview(e.target.checked)} />
        Aperçu gratuit (consultable sans achat)
      </label>

      <button onClick={handleAdd} disabled={uploading} className="btn-outline self-start !py-1.5 !text-xs">
        {uploading ? <Loader2 size={14} className="animate-spin" /> : <PlusCircle size={14} />}
        {uploading ? "Envoi en cours..." : "Ajouter la vidéo"}
      </button>
    </div>
  );
}

function AddPdfForm({ onAdd }: { onAdd: (title: string, pageCount: number, file: File | null, isFreeSample: boolean) => void }) {
  const [title, setTitle] = useState("");
  const [pages, setPages] = useState("10");
  const [file, setFile] = useState<File | null>(null);
  const [freeSample, setFreeSample] = useState(false);
  const [uploading, setUploading] = useState(false);

  async function handleAdd() {
    if (!title) return;
    setUploading(true);
    try {
      await onAdd(title, Number(pages) || 0, file, freeSample);
      setTitle(""); setFile(null); setFreeSample(false);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="mt-3 flex flex-col gap-2 border-t border-gray-100 pt-3">
      <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Titre du PDF"
        className="rounded-lg border border-gray-200 px-3 py-2 text-sm" />
      <input value={pages} onChange={(e) => setPages(e.target.value)} type="number" placeholder="Nombre de pages"
        className="rounded-lg border border-gray-200 px-3 py-2 text-sm" />
      <input type="file" accept="application/pdf" onChange={(e) => setFile(e.target.files?.[0] || null)}
        className="rounded-lg border border-dashed border-gray-300 px-3 py-2 text-sm" />
      <label className="flex items-center gap-2 text-xs text-gray-600">
        <input type="checkbox" checked={freeSample} onChange={(e) => setFreeSample(e.target.checked)} />
        Extrait gratuit (consultable sans achat)
      </label>
      <button onClick={handleAdd} disabled={uploading} className="btn-outline self-start !py-1.5 !text-xs">
        {uploading ? <Loader2 size={14} className="animate-spin" /> : <PlusCircle size={14} />}
        {uploading ? "Envoi en cours..." : "Ajouter le PDF"}
      </button>
    </div>
  );
}
