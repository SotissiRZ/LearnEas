"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Save } from "lucide-react";
import { api } from "@/lib/api";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import DashboardNav from "@/components/dashboard/DashboardNav";
import GuardScreen from "@/components/ui/GuardScreen";

export default function NewFormationPage() {
  const { ready } = useAuthGuard({ roles: ["instructor", "admin"], redirectTo: "/dashboard/instructor" });
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    title: "", description: "", level: "beginner", language: "Français",
    price: "0", num_sessions: "4", session_duration_minutes: "60",
    max_students: "10", start_date: "", end_date: "",
  });

  function set<K extends keyof typeof form>(key: K, value: (typeof form)[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const formation = await api.post<{ id: number }>("/formations/", {
        ...form,
        price: Number(form.price),
        num_sessions: Number(form.num_sessions),
        session_duration_minutes: Number(form.session_duration_minutes),
        max_students: Number(form.max_students),
        start_date: form.start_date || null,
        end_date: form.end_date || null,
        status: "scheduled",
      });
      router.push(`/dashboard/instructor/formations`);
    } catch (err: any) {
      setError(err.message || "Erreur lors de la création de la formation.");
    } finally {
      setSaving(false);
    }
  }

  if (!ready) return <GuardScreen />;

  return (
    <div className="container-app py-10">
      <DashboardNav role="instructor" />
      <div className="card max-w-2xl p-6">
        <h1 className="mb-1 text-xl font-bold">Créer une formation interactive</h1>
        <p className="mb-6 text-sm text-gray-500">
          Séances en direct planifiées avec vos apprenants inscrits — ajoutez les créneaux
          (date, lien de visioconférence) une fois la formation créée.
        </p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div>
            <label className="mb-1 block text-sm font-medium">Titre</label>
            <input required value={form.title} onChange={(e) => set("title", e.target.value)}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" placeholder="Ex: Coaching React en petit groupe" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Description</label>
            <textarea required rows={4} value={form.description} onChange={(e) => set("description", e.target.value)}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium">Niveau</label>
              <select value={form.level} onChange={(e) => set("level", e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm">
                <option value="beginner">Débutant</option>
                <option value="intermediate">Intermédiaire</option>
                <option value="expert">Expert</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Prix (MAD)</label>
              <input type="number" min={0} value={form.price} onChange={(e) => set("price", e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium">Nb. séances</label>
              <input type="number" min={1} value={form.num_sessions} onChange={(e) => set("num_sessions", e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Durée/séance (min)</label>
              <input type="number" min={15} value={form.session_duration_minutes} onChange={(e) => set("session_duration_minutes", e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Places max.</label>
              <input type="number" min={1} value={form.max_students} onChange={(e) => set("max_students", e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium">Date de début</label>
              <input type="date" value={form.start_date} onChange={(e) => set("start_date", e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Date de fin</label>
              <input type="date" value={form.end_date} onChange={(e) => set("end_date", e.target.value)}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" />
            </div>
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <button type="submit" disabled={saving} className="btn-primary">
            {saving ? <Loader2 className="animate-spin" size={16} /> : <Save size={16} />}
            Créer la formation
          </button>
        </form>
      </div>
    </div>
  );
}
