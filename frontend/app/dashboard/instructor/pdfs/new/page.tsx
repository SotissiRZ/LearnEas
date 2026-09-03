"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Save, Upload } from "lucide-react";
import { api, apiUploadWithProgress, ApiError } from "@/lib/api";
import { Category } from "@/types";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import GuardScreen from "@/components/ui/GuardScreen";
import UploadProgressBar from "@/components/ui/UploadProgressBar";

export default function NewPdfPage() {
  const { ready } = useAuthGuard({ roles: ["instructor", "admin"], redirectTo: "/dashboard/instructor" });
  const router = useRouter();
  const [categories, setCategories] = useState<Category[]>([]);
  const [saving, setSaving] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [cover, setCover] = useState<File | null>(null);
  const [form, setForm] = useState({
    title: "", description: "", category: "", level: "beginner",
    language: "Français", price: "0", is_free: false,
  });

  useEffect(() => {
    api.get<Category[]>("/catalog/categories/").then(setCategories).catch(() => {});
  }, []);

  function set<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!form.title.trim()) { setError("Le titre est obligatoire."); return; }
    if (!form.description.trim()) { setError("La description est obligatoire."); return; }
    if (!file) { setError("Veuillez sélectionner un fichier PDF."); return; }

    setSaving(true);
    setProgress(0);
    try {
      const fd = new FormData();
      fd.append("title", form.title);
      fd.append("description", form.description);
      fd.append("level", form.level);
      fd.append("language", form.language);
      fd.append("price", form.is_free ? "0" : form.price);
      fd.append("is_free", String(form.is_free));
      if (form.category) fd.append("category", form.category);
      fd.append("file", file);
      if (cover) fd.append("cover_image", cover);

      await apiUploadWithProgress("/catalog/pdfs/", fd, setProgress);
      router.push("/dashboard/instructor/pdfs");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erreur lors de la création du PDF.");
    } finally {
      setSaving(false);
    }
  }

  if (!ready) return <GuardScreen />;

  return (
    <div className="min-w-0">
      <div className="card max-w-2xl p-6">
        <h1 className="mb-1 text-xl font-bold">Publier un nouveau PDF</h1>
        <p className="mb-6 text-sm text-gray-500">Vendu indépendamment, dans votre propre catalogue PDF.</p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="mb-1 block text-sm font-medium">Titre</label>
            <input required value={form.title} onChange={(e) => set("title", e.target.value)}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Description</label>
            <textarea required rows={4} value={form.description} onChange={(e) => set("description", e.target.value)}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium">Catégorie</label>
              <select value={form.category} onChange={(e) => set("category", e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm">
                <option value="">-</option>
                {categories.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Niveau</label>
              <select value={form.level} onChange={(e) => set("level", e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm">
                <option value="beginner">Débutant</option>
                <option value="intermediate">Intermédiaire</option>
                <option value="expert">Expert</option>
              </select>
            </div>
          </div>

          <div>
            <label className="mb-1 block text-sm font-medium">Prix (EUR)</label>
            <input type="number" min={0} value={form.price} onChange={(e) => set("price", e.target.value)}
              disabled={form.is_free} className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm disabled:bg-gray-50" />
          </div>

          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={form.is_free} onChange={(e) => set("is_free", e.target.checked)} />
            PDF gratuit
          </label>

          <div>
            <label className="mb-1 flex items-center gap-2 text-sm font-medium"><Upload size={16} /> Image de couverture</label>
            <input type="file" accept="image/*" onChange={(e) => setCover(e.target.files?.[0] || null)}
              className="w-full rounded-lg border border-dashed border-gray-300 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="mb-1 flex items-center gap-2 text-sm font-medium"><Upload size={16} /> Fichier PDF</label>
            <input required type="file" accept="application/pdf" onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="w-full rounded-lg border border-dashed border-gray-300 px-3 py-2 text-sm" />
            <p className="mt-1 text-xs text-gray-400">Le nombre de pages est extrait automatiquement.</p>
          </div>

          {saving && <UploadProgressBar percent={progress} label="Envoi du PDF..." />}
          {error && <p className="text-sm text-red-600">{error}</p>}

          <button type="submit" disabled={saving} className="btn-primary">
            {saving ? <Loader2 className="animate-spin" size={16} /> : <Save size={16} />}
            Publier (brouillon)
          </button>
        </form>
      </div>
    </div>
  );
}
