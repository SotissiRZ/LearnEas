"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import { api, ApiError } from "@/lib/api";
import DashboardNav from "@/components/dashboard/DashboardNav";
import GuardScreen from "@/components/ui/GuardScreen";
import CountrySelect from "@/components/ui/CountrySelect";
import WhatsAppPreferencesCard from "@/components/notifications/WhatsAppPreferencesCard";
import { Loader2, Save } from "lucide-react";

export default function StudentProfilePage() {
  const { user, ready } = useAuthGuard();
  const { refreshMe } = useAuth();
  const [form, setForm] = useState({ first_name: "", last_name: "", headline: "", country: "" });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!user) return;
    setForm({
      first_name: user.first_name || "",
      last_name: user.last_name || "",
      headline: user.headline || "",
      country: user.country || "",
    });
  }, [user?.id, user?.first_name, user?.last_name, user?.headline, user?.country]);

  async function handleSave() {
    if (!form.country) {
      setMessage("Sélectionnez votre pays.");
      return;
    }
    setSaving(true);
    setMessage("");
    try {
      await api.patch("/auth/me/", form);
      await refreshMe();
      setMessage("Profil enregistré.");
    } catch (error) {
      setMessage(error instanceof ApiError ? error.message : "Impossible d'enregistrer le profil.");
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
              <input
                value={form.first_name}
                onChange={(e) => setForm({ ...form, first_name: e.target.value })}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Nom</label>
              <input
                value={form.last_name}
                onChange={(e) => setForm({ ...form, last_name: e.target.value })}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Email</label>
              <input
                value={user.email}
                disabled
                className="w-full rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-400"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Pays</label>
              <CountrySelect
                required
                value={form.country}
                onChange={(country) => setForm({ ...form, country })}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
              />
              <p className="mt-1 text-[11px] text-gray-400">Le pays sert notamment à proposer la devise et les moyens de paiement locaux adaptés.</p>
            </div>
            {message && <p className={`text-xs ${message.includes("enregistré") ? "text-emerald-700" : "text-red-600"}`}>{message}</p>}
            <button onClick={handleSave} disabled={saving} className="btn-primary">
              {saving ? <Loader2 className="animate-spin" size={16} /> : <Save size={16} />}
              {saving ? "Enregistrement..." : "Enregistrer"}
            </button>
          </div>
        </div>
        <WhatsAppPreferencesCard />
      </div>
    </div>
  );
}
