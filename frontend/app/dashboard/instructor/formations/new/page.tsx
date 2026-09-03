"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { ImagePlus, Loader2, Save } from "lucide-react";
import { apiUploadWithProgress, ApiError } from "@/lib/api";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import GuardScreen from "@/components/ui/GuardScreen";
import UploadProgressBar from "@/components/ui/UploadProgressBar";

export default function NewFormationPage() {
  const { ready } = useAuthGuard({ roles: ["instructor", "admin"], redirectTo: "/dashboard/instructor" });
  const router = useRouter();
  const [saving, setSaving] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const [cover, setCover] = useState<File | null>(null);
  const [form, setForm] = useState({
    title: "", description: "", level: "beginner", language: "Français",
    price: "0", num_sessions: "4", session_duration_minutes: "60",
    max_students: "10", min_students: "5", start_date: "", end_date: "",
    cohort_name: "", cohort_timezone: "Africa/Abidjan", enrollment_deadline: "",
  });
  function set<K extends keyof typeof form>(key: K, value: (typeof form)[K]) { setForm((f) => ({ ...f, [key]: value })); }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault(); setSaving(true); setProgress(0); setError("");
    try {
      const fd = new FormData();
      Object.entries(form).forEach(([key, value]) => { if (value) fd.append(key, value); });
      if (form.enrollment_deadline) fd.set("enrollment_deadline", new Date(form.enrollment_deadline).toISOString());
      fd.set("status", "scheduled");
      if (cover) fd.append("thumbnail", cover);
      await apiUploadWithProgress<{ id: number }>("/formations/", fd, setProgress);
      router.push("/dashboard/instructor/formations");
    } catch (err) { setError(err instanceof ApiError ? err.message : "Erreur lors de la création de la formation."); }
    finally { setSaving(false); }
  }

  if (!ready) return <GuardScreen />;
  return <div className="min-w-0"><div className="card max-w-2xl p-6">
    <h1 className="mb-1 text-xl font-bold">Créer une cohorte live</h1>
    <p className="mb-6 text-sm text-gray-500">Définissez la cohorte, les places et la période d’inscription, puis planifiez les séances live LearnEas.</p>
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div><label className="mb-1 block text-sm font-medium">Titre</label><input required value={form.title} onChange={(e) => set("title", e.target.value)} className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" placeholder="Ex: Coaching React en petit groupe" /></div>
      <div><label className="mb-1 block text-sm font-medium">Description</label><textarea required rows={4} value={form.description} onChange={(e) => set("description", e.target.value)} className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" /></div>
      <div className="grid gap-4 sm:grid-cols-2"><div><label className="mb-1 block text-sm font-medium">Nom de la cohorte</label><input value={form.cohort_name} onChange={(e) => set("cohort_name", e.target.value)} className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" placeholder="Ex : Cohorte Octobre 2026" /></div><div><label className="mb-1 block text-sm font-medium">Fuseau horaire</label><input value={form.cohort_timezone} onChange={(e) => set("cohort_timezone", e.target.value)} className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" placeholder="Africa/Abidjan" /></div></div>
      <div><label className="mb-1 flex items-center gap-2 text-sm font-medium"><ImagePlus size={16} /> Image de couverture</label><input type="file" accept="image/*" onChange={(e) => setCover(e.target.files?.[0] || null)} className="w-full rounded-lg border border-dashed border-gray-300 px-3 py-2 text-sm" /></div>
      <div className="grid grid-cols-2 gap-4"><div><label className="mb-1 block text-sm font-medium">Niveau</label><select value={form.level} onChange={(e) => set("level", e.target.value)} className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"><option value="beginner">Débutant</option><option value="intermediate">Intermédiaire</option><option value="expert">Expert</option></select></div><div><label className="mb-1 block text-sm font-medium">Prix (EUR)</label><input type="number" min={0} value={form.price} onChange={(e) => set("price", e.target.value)} className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" /></div></div>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4"><div><label className="mb-1 block text-sm font-medium">Nb. séances</label><input type="number" min={1} value={form.num_sessions} onChange={(e) => set("num_sessions", e.target.value)} className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" /></div><div><label className="mb-1 block text-sm font-medium">Durée/séance (min)</label><input type="number" min={15} value={form.session_duration_minutes} onChange={(e) => set("session_duration_minutes", e.target.value)} className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" /></div><div><label className="mb-1 block text-sm font-medium">Places max.</label><input type="number" min={1} value={form.max_students} onChange={(e) => set("max_students", e.target.value)} className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" /></div><div><label className="mb-1 block text-sm font-medium">Participants min.</label><input type="number" min={1} value={form.min_students} onChange={(e) => set("min_students", e.target.value)} className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" /></div></div>
      <div className="grid gap-4 sm:grid-cols-3"><div><label className="mb-1 block text-sm font-medium">Date de début</label><input type="date" value={form.start_date} onChange={(e) => set("start_date", e.target.value)} className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" /></div><div><label className="mb-1 block text-sm font-medium">Date de fin</label><input type="date" value={form.end_date} onChange={(e) => set("end_date", e.target.value)} className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" /></div><div><label className="mb-1 block text-sm font-medium">Clôture inscriptions</label><input type="datetime-local" value={form.enrollment_deadline} onChange={(e) => set("enrollment_deadline", e.target.value)} className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" /></div></div>
      {saving && <UploadProgressBar percent={progress} label="Création de la cohorte..." />}{error && <p className="text-sm text-red-600">{error}</p>}
      <button type="submit" disabled={saving} className="btn-primary">{saving ? <Loader2 className="animate-spin" size={16} /> : <Save size={16} />}Créer la cohorte</button>
    </form>
  </div></div>;
}
