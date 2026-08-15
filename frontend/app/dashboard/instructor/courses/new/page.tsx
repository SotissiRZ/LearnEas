"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Save } from "lucide-react";
import { api } from "@/lib/api";
import { Category } from "@/types";
import DashboardNav from "@/components/dashboard/DashboardNav";

export default function NewCoursePage() {
  const router = useRouter();
  const [categories, setCategories] = useState<Category[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    title: "", subtitle: "", description: "", category: "", level: "beginner",
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
    setSaving(true);
    setError("");
    try {
      const course = await api.post<{ id: number }>("/catalog/courses/", {
        ...form,
        category: form.category ? Number(form.category) : null,
        price: Number(form.price),
        what_you_will_learn: [],
        requirements: [],
        target_audience: [],
      });
      router.push(`/dashboard/instructor/courses/${course.id}`);
    } catch (err: any) {
      setError(err.message || "Erreur lors de la création du cours.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="container-app py-10">
      <DashboardNav role="instructor" />
      <div className="card max-w-2xl p-6">
        <h1 className="mb-1 text-xl font-bold">Créer un nouveau cours</h1>
        <p className="mb-6 text-sm text-gray-500">
          Vous pourrez ensuite ajouter vos sections, vidéos et PDF depuis la page de gestion du cours.
        </p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="mb-1 block text-sm font-medium">Titre du cours</label>
            <input required value={form.title} onChange={(e) => set("title", e.target.value)}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" placeholder="Ex: Django REST Framework de A à Z" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Sous-titre</label>
            <input value={form.subtitle} onChange={(e) => set("subtitle", e.target.value)}
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
                <option value="">—</option>
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

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium">Prix (MAD)</label>
              <input type="number" min={0} value={form.price} onChange={(e) => set("price", e.target.value)}
                disabled={form.is_free}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm disabled:bg-gray-50" />
            </div>
            <label className="mt-6 flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.is_free} onChange={(e) => set("is_free", e.target.checked)} />
              Cours gratuit
            </label>
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button type="submit" disabled={saving} className="btn-primary">
            {saving ? <Loader2 className="animate-spin" size={16} /> : <Save size={16} />}
            Créer le cours (brouillon)
          </button>
        </form>
      </div>
    </div>
  );
}
