"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Loader2, Mail, MessageCircle, Save } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import InternationalPhoneField from "@/components/ui/InternationalPhoneField";

type NotificationPreferences = {
  whatsapp_phone: string;
  whatsapp_opt_in: boolean;
  whatsapp_payment_enabled: boolean;
  whatsapp_live_enabled: boolean;
  whatsapp_inactivity_enabled: boolean;
  whatsapp_certificate_enabled: boolean;
  whatsapp_recruitment_enabled: boolean;
  whatsapp_consent_at: string | null;
  in_app_enabled: boolean;
  email_enabled: boolean;
  email_payment_enabled: boolean;
  email_live_enabled: boolean;
  email_inactivity_enabled: boolean;
  email_certificate_enabled: boolean;
  email_recruitment_enabled: boolean;
  updated_at: string;
};

export default function WhatsAppPreferencesCard() {
  const user = useAuth((state) => state.user);
  const [form, setForm] = useState<NotificationPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<NotificationPreferences>("/notifications/preferences/")
      .then(setForm)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Impossible de charger les préférences de notifications."))
      .finally(() => setLoading(false));
  }, []);

  async function save() {
    if (!form) return;
    setSaving(true); setError(""); setMessage("");
    try {
      const updated = await api.patch<NotificationPreferences>("/notifications/preferences/", form);
      setForm(updated);
      setMessage("Préférences de notifications enregistrées.");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Impossible d'enregistrer les préférences de notifications.");
    } finally { setSaving(false); }
  }

  if (loading) return <div className="card p-5 text-sm text-gray-400">Chargement des notifications...</div>;
  if (!form) return <div className="card p-5 text-sm text-red-600">{error || "Préférences de notifications indisponibles."}</div>;

  const toggle = (key: keyof NotificationPreferences, value: boolean) => setForm({ ...form, [key]: value });
  return (
    <section className="card p-5">
      <div className="flex items-start gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-brand-50 text-brand-700"><Mail size={20}/></span>
        <div><h2 className="font-bold">Notifications KalanPro</h2><p className="mt-1 text-xs leading-5 text-gray-500">Choisissez les canaux utiles. Les emails transactionnels sont envoyés avec le design KalanPro via Resend ; WhatsApp reste soumis à votre consentement explicite.</p></div>
      </div>

      <div className="mt-5 rounded-2xl border border-gray-100 p-4">
        <div className="mb-3 flex items-center gap-2"><CheckCircle2 size={17} className="text-brand-700"/><h3 className="font-bold">Centre KalanPro</h3></div>
        <Toggle title="Notifications dans KalanPro" description="Affiche les alertes dans la cloche et le centre de notifications." checked={form.in_app_enabled} onChange={v=>toggle("in_app_enabled",v)}/>
      </div>

      <div className="mt-4 rounded-2xl border border-gray-100 p-4">
        <div className="mb-3 flex items-center gap-2"><Mail size={17} className="text-brand-700"/><h3 className="font-bold">Email</h3><span className="rounded-full bg-orange-50 px-2 py-1 text-[10px] font-bold text-orange-700">Resend</span></div>
        <Toggle title="Activer les emails" description={`Envoyés à ${user?.email || "votre adresse de compte"}.`} checked={form.email_enabled} onChange={v=>toggle("email_enabled",v)}/>
        {form.email_enabled && <div className="mt-3 grid gap-2 rounded-xl bg-gray-50 p-3 sm:grid-cols-2">
          <Toggle compact title="Paiements confirmés" checked={form.email_payment_enabled} onChange={v=>toggle("email_payment_enabled",v)}/>
          <Toggle compact title="Rappels de live" checked={form.email_live_enabled} onChange={v=>toggle("email_live_enabled",v)}/>
          <Toggle compact title="Reprendre un cours" checked={form.email_inactivity_enabled} onChange={v=>toggle("email_inactivity_enabled",v)}/>
          <Toggle compact title="Certificats disponibles" checked={form.email_certificate_enabled} onChange={v=>toggle("email_certificate_enabled",v)}/>
          <Toggle compact title="Candidatures & recrutement" checked={form.email_recruitment_enabled} onChange={v=>toggle("email_recruitment_enabled",v)}/>
        </div>}
      </div>

      <div className="mt-4 rounded-2xl border border-gray-100 p-4">
        <div className="mb-3 flex items-center gap-2"><MessageCircle size={17} className="text-emerald-700"/><h3 className="font-bold">WhatsApp</h3></div>
        <InternationalPhoneField
          value={form.whatsapp_phone}
          onChange={(whatsapp_phone) => setForm({ ...form, whatsapp_phone })}
          preferredCountry={user?.country}
          label="Numéro WhatsApp"
          helperText="Choisissez le pays / indicatif puis saisissez uniquement le numéro national. KalanPro enregistre automatiquement le format international E.164."
        />
        <div className="mt-3"><Toggle title="Activer WhatsApp" description="Consentement aux notifications transactionnelles KalanPro." checked={form.whatsapp_opt_in} onChange={v=>toggle("whatsapp_opt_in",v)}/></div>
        {form.whatsapp_opt_in && <div className="mt-3 grid gap-2 rounded-xl bg-gray-50 p-3 sm:grid-cols-2">
          <Toggle compact title="Paiements confirmés" checked={form.whatsapp_payment_enabled} onChange={v=>toggle("whatsapp_payment_enabled",v)}/>
          <Toggle compact title="Rappels de live" checked={form.whatsapp_live_enabled} onChange={v=>toggle("whatsapp_live_enabled",v)}/>
          <Toggle compact title="Reprendre un cours" checked={form.whatsapp_inactivity_enabled} onChange={v=>toggle("whatsapp_inactivity_enabled",v)}/>
          <Toggle compact title="Certificats disponibles" checked={form.whatsapp_certificate_enabled} onChange={v=>toggle("whatsapp_certificate_enabled",v)}/>
          <Toggle compact title="Candidatures & recrutement" checked={form.whatsapp_recruitment_enabled} onChange={v=>toggle("whatsapp_recruitment_enabled",v)}/>
        </div>}
        {form.whatsapp_consent_at && form.whatsapp_opt_in && <p className="mt-2 flex items-center gap-1 text-[11px] text-emerald-700"><CheckCircle2 size={13}/> Consentement WhatsApp enregistré.</p>}
      </div>

      {error && <p className="mt-3 text-xs text-red-600">{error}</p>}{message && <p className="mt-3 text-xs text-emerald-700">{message}</p>}
      <button type="button" onClick={save} disabled={saving} className="btn-primary mt-4 w-full sm:w-auto">{saving?<Loader2 className="animate-spin" size={15}/>:<Save size={15}/>} Enregistrer les notifications</button>
    </section>
  );
}

function Toggle({title,description,checked,onChange,compact=false}:{title:string;description?:string;checked:boolean;onChange:(v:boolean)=>void;compact?:boolean}){
  return <label className={`flex cursor-pointer items-center justify-between gap-3 ${compact?"rounded-lg bg-white px-3 py-2":"rounded-xl border border-gray-100 px-3 py-3"}`}><span><span className="block text-sm font-semibold">{title}</span>{description&&<span className="mt-0.5 block text-[11px] text-gray-400">{description}</span>}</span><input type="checkbox" checked={checked} onChange={e=>onChange(e.target.checked)} className="h-4 w-4 accent-brand-600"/></label>
}
