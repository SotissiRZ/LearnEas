"use client";

import { useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import { api } from "@/lib/api";
import DashboardNav from "@/components/dashboard/DashboardNav";
import GuardScreen from "@/components/ui/GuardScreen";
import { Save, Loader2 } from "lucide-react";
import WhatsAppPreferencesCard from "@/components/notifications/WhatsAppPreferencesCard";

export default function StudentProfilePage() {
  const { user, ready } = useAuthGuard();
  const { refreshMe } = useAuth();
  const [form, setForm] = useState({
    first_name: user?.first_name || "",
    last_name: user?.last_name || "",
    headline: user?.headline || "",
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  async function handleSave() {
    setSaving(true);
    try {
      await api.patch("/auth/me/", form);
      await refreshMe();
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } finally {
      setSaving(false);
    }
  }

  if (!ready || !user) return <GuardScreen />;

  return (
    <div className="container-app py-10">
      <DashboardNav role="student" />
      <div className="max-w-lg space-y-5">
      <div className="card p-6">
        <h2 className="mb-4 text-xl font-bold">Mon profil</h2>
        <div className="flex flex-col gap-4">
          <div>
            <label className="mb-1 block text-sm font-medium">Prénom</label>
            <input value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Nom</label>
            <input value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })}
              className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">Email</label>
            <input value={user.email} disabled className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-400" />
          </div>
          <button onClick={handleSave} disabled={saving} className="btn-primary">
            {saving ? <Loader2 className="animate-spin" size={16} /> : <Save size={16} />}
            {saved ? "Enregistré !" : "Enregistrer"}
          </button>
        </div>
      </div>
      <WhatsAppPreferencesCard />
      </div>
    </div>
  );
}
