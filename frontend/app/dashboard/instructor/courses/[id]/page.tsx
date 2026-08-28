"use client";

import { useEffect, useState, useCallback } from "react";
import { PlusCircle, Trash2, PlayCircle, FileText, Eye, EyeOff, Loader2, Upload, Link as LinkIcon, AlertCircle } from "lucide-react";
import { api, apiUploadWithProgress, ApiError } from "@/lib/api";
import { Course } from "@/types";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import GuardScreen from "@/components/ui/GuardScreen";
import UploadProgressBar from "@/components/ui/UploadProgressBar";
import PdfViewer from "@/components/ui/PdfViewer";

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

  async function addLessonByFile(
    sectionId: number, title: string, file: File, isPreview: boolean,
    onProgress: (percent: number) => void
  ) {
    const fd = new FormData();
    fd.append("section", String(sectionId));
    fd.append("title", title);
    fd.append("order", "1");
    fd.append("is_preview", String(isPreview));
    fd.append("video_file", file);
    await apiUploadWithProgress("/catalog/lessons/", fd, onProgress);
    load();
  }

  async function addPdf(
    title: string, file: File, cover: File | null, isFreeSample: boolean,
    onProgress: (percent: number) => void
  ) {
    if (!course) return;
    const fd = new FormData();
    fd.append("course", String(course.id));
    fd.append("title", title);
    fd.append("is_free_sample", String(isFreeSample));
    fd.append("order", "1");
    fd.append("file", file);
    if (cover) fd.append("cover_image", cover);
    await apiUploadWithProgress("/catalog/pdf-resources/", fd, onProgress);
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
    <div className="min-w-0">

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
                    {(lesson.video_file || lesson.video_url) && (
                      <a href={lesson.video_file || lesson.video_url || "#"} target="_blank" rel="noreferrer"
                        className="font-semibold text-brand-700">Lire</a>
                    )}
                    <button onClick={() => deleteLesson(lesson.id)} className="text-gray-400 hover:text-red-600">
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
              </div>
              <AddLessonForm
                onAddUrl={(title, duration, url, preview) => addLessonByUrl(section.id, title, duration, url, preview)}
                onAddFile={(title, file, preview, onProgress) => addLessonByFile(section.id, title, file, preview, onProgress)}
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
                  {pdf.cover_image ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={pdf.cover_image} alt="" className="h-9 w-7 rounded object-cover" />
                  ) : <FileText size={14} className="text-amber-600" />}
                  <span className="flex-1 line-clamp-1">{pdf.title} · {pdf.page_count} p.</span>
                  {pdf.is_free_sample && <span className="badge bg-brand-50 text-brand-700">Extrait</span>}
                  {pdf.file && <PdfViewer url={pdf.file} title={pdf.title} />}
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

async function extractVideoDurationFromUrl(url: string): Promise<number> {
  return new Promise((resolve, reject) => {
    const video = document.createElement("video");
    const timer = window.setTimeout(() => {
      video.src = "";
      reject(new Error("Impossible de lire les métadonnées de cette URL vidéo."));
    }, 12000);
    video.preload = "metadata";
    video.onloadedmetadata = () => {
      window.clearTimeout(timer);
      const seconds = video.duration;
      video.src = "";
      if (!Number.isFinite(seconds) || seconds <= 0) {
        reject(new Error("Durée vidéo invalide."));
        return;
      }
      resolve(Math.max(1, Math.ceil(seconds / 60)));
    };
    video.onerror = () => {
      window.clearTimeout(timer);
      reject(new Error("Impossible d'extraire la durée de cette URL vidéo."));
    };
    video.src = url;
  });
}

function AddLessonForm({
  onAddUrl, onAddFile,
}: {
  onAddUrl: (title: string, duration: number, url: string, preview: boolean) => Promise<void>;
  onAddFile: (title: string, file: File, preview: boolean, onProgress: (p: number) => void) => Promise<void>;
}) {
  const [mode, setMode] = useState<"file" | "url">("file");
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const [fileInputKey, setFileInputKey] = useState(0);

  async function handleAdd() {
    setError("");
    if (!title.trim()) { setError("Le titre de la vidéo est obligatoire."); return; }
    if (mode === "file" && !file) { setError("Sélectionnez un fichier vidéo, ou basculez sur \"Lien externe\"."); return; }
    if (mode === "url" && !url.trim()) { setError("Indiquez un lien vidéo, ou basculez sur \"Uploader un fichier\"."); return; }

    setUploading(true);
    setProgress(0);
    try {
      if (mode === "file" && file) {
        await onAddFile(title, file, preview, setProgress);
      } else if (mode === "url") {
        const minutes = await extractVideoDurationFromUrl(url);
        await onAddUrl(title, minutes, url, preview);
      }
      setTitle(""); setUrl(""); setFile(null); setPreview(false); setProgress(0);
      setFileInputKey((k) => k + 1); // réinitialise visuellement le champ fichier natif
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de l'ajout de la vidéo.");
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

      <div>
        <label className="mb-0.5 block text-xs font-medium text-gray-500">Titre de la vidéo</label>
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Ex: Introduction aux hooks"
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" />
        <p className="mt-1 text-xs text-gray-400">La durée est extraite automatiquement des métadonnées de la vidéo.</p>
      </div>

      {mode === "file" ? (
        <div>
          <label className="mb-0.5 block text-xs font-medium text-gray-500">Fichier vidéo</label>
          <input key={fileInputKey} type="file" accept="video/*" onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="w-full rounded-lg border border-dashed border-gray-300 px-3 py-2 text-sm" />
        </div>
      ) : (
        <div>
          <label className="mb-0.5 block text-xs font-medium text-gray-500">Lien vidéo</label>
          <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://... (mp4 ou flux vidéo)"
            className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" />
        </div>
      )}

      <label className="flex items-center gap-2 text-xs text-gray-600">
        <input type="checkbox" checked={preview} onChange={(e) => setPreview(e.target.checked)} />
        Aperçu gratuit (consultable sans achat)
      </label>

      {uploading && mode === "file" && <UploadProgressBar percent={progress} label="Envoi de la vidéo..." />}

      {error && (
        <p className="flex items-center gap-1 text-xs text-red-600"><AlertCircle size={12} /> {error}</p>
      )}

      <button onClick={handleAdd} disabled={uploading} className="btn-outline self-start !py-1.5 !text-xs">
        {uploading ? <Loader2 size={14} className="animate-spin" /> : <PlusCircle size={14} />}
        {uploading ? "Envoi en cours..." : "Ajouter la vidéo"}
      </button>
    </div>
  );
}

function AddPdfForm({
  onAdd,
}: {
  onAdd: (title: string, file: File, cover: File | null, isFreeSample: boolean, onProgress: (p: number) => void) => Promise<void>;
}) {
  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [cover, setCover] = useState<File | null>(null);
  const [freeSample, setFreeSample] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const [fileInputKey, setFileInputKey] = useState(0);

  async function handleAdd() {
    setError("");
    if (!title.trim()) { setError("Le titre du PDF est obligatoire."); return; }
    if (!file) { setError("Sélectionnez un fichier PDF."); return; }

    setUploading(true);
    setProgress(0);
    try {
      await onAdd(title, file, cover, freeSample, setProgress);
      setTitle(""); setFile(null); setCover(null); setFreeSample(false); setProgress(0);
      setFileInputKey((k) => k + 1);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de l'ajout du PDF.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="mt-3 flex flex-col gap-2 border-t border-gray-100 pt-3">
      <div>
        <label className="mb-0.5 block text-xs font-medium text-gray-500">Titre du PDF</label>
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Ex: Support de cours"
          className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" />
      </div>
      <div>
        <label className="mb-0.5 block text-xs font-medium text-gray-500">Image de couverture (optionnelle)</label>
        <input key={`cover-${fileInputKey}`} type="file" accept="image/*" onChange={(e) => setCover(e.target.files?.[0] || null)}
          className="w-full rounded-lg border border-dashed border-gray-300 px-3 py-2 text-sm" />
      </div>
      <div>
        <label className="mb-0.5 block text-xs font-medium text-gray-500">Fichier PDF</label>
        <input key={`pdf-${fileInputKey}`} type="file" accept="application/pdf" onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="w-full rounded-lg border border-dashed border-gray-300 px-3 py-2 text-sm" />
        <p className="mt-1 text-xs text-gray-400">Le nombre de pages est détecté automatiquement.</p>
      </div>
      <label className="flex items-center gap-2 text-xs text-gray-600">
        <input type="checkbox" checked={freeSample} onChange={(e) => setFreeSample(e.target.checked)} />
        Extrait gratuit (consultable sans achat)
      </label>

      {uploading && <UploadProgressBar percent={progress} label="Envoi du PDF..." />}

      {error && (
        <p className="flex items-center gap-1 text-xs text-red-600"><AlertCircle size={12} /> {error}</p>
      )}

      <button onClick={handleAdd} disabled={uploading} className="btn-outline self-start !py-1.5 !text-xs">
        {uploading ? <Loader2 size={14} className="animate-spin" /> : <PlusCircle size={14} />}
        {uploading ? "Envoi en cours..." : "Ajouter le PDF"}
      </button>
    </div>
  );
}
