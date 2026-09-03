"use client";

import { useEffect, useState } from "react";
import { CheckCircle2, Loader2, MessageCircle, Save } from "lucide-react";
import { api, ApiError } from "@/lib/api";

type WhatsAppPreferences = {
  whatsapp_phone: string;
  whatsapp_opt_in: boolean;
  whatsapp_payment_enabled: boolean;
  whatsapp_live_enabled: boolean;
  whatsapp_inactivity_enabled: boolean;
  whatsapp_certificate_enabled: boolean;
  whatsapp_consent_at: string | null;
  updated_at: string;
};

export default function WhatsAppPreferencesCard() {
  const [form, setForm] = useState<WhatsAppPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<WhatsAppPreferences>("/notifications/preferences/")
      .then(setForm)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Impossible de charger les préférences WhatsApp."))
      .finally(() => setLoading(false));
  }, []);

  async function save() {
    if (!form) return;
    setSaving(true); setError(""); setMessage("");
    try {
      const updated = await api.patch<WhatsAppPreferences>("/notifications/preferences/", form);
      setForm(updated);
      setMessage("Préférences WhatsApp enregistrées.");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Impossible d'enregistrer les préférences WhatsApp.");
    } finally { setSaving(false); }
  }

  if (loading) return <div className="card p-5 text-sm text-gray-400">Chargement des notifications WhatsApp...</div>;
  if (!form) return <div className="card p-5 text-sm text-red-600">{error || "Préférences WhatsApp indisponibles."}</div>;

  const toggle = (key: keyof WhatsAppPreferences, value: boolean) => setForm({ ...form, [key]: value });
  return (
    <section className="card p-5">
      <div className="flex items-start gap-3">
        <span className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-emerald-50 text-emerald-700"><MessageCircle size={20}/></span>
        <div><h2 className="font-bold">Notifications WhatsApp</h2><p className="mt-1 text-xs leading-5 text-gray-500">Recevez uniquement les informations utiles liées à vos achats et formations. Vous pouvez retirer votre accord à tout moment.</p></div>
      </div>
      <div className="mt-4 space-y-4">
        <label className="block"><span className="mb-1 block text-xs font-medium text-gray-500">Numéro WhatsApp international</span><input className="input-admin w-full" inputMode="tel" placeholder="+221771234567" value={form.whatsapp_phone} onChange={e=>setForm({...form,whatsapp_phone:e.target.value})}/><span className="mt-1 block text-[11px] text-gray-400">Ex. Sénégal +221, Côte d'Ivoire +225, Cameroun +237. Ne mettez pas le 0 national après l'indicatif.</span></label>
        <Toggle title="Activer WhatsApp" description="Consentement aux notifications transactionnelles LearnEas." checked={form.whatsapp_opt_in} onChange={v=>toggle("whatsapp_opt_in",v)}/>
        {form.whatsapp_opt_in && <div className="grid gap-2 rounded-xl border border-gray-100 bg-gray-50 p-3 sm:grid-cols-2">
          <Toggle compact title="Paiements confirmés" checked={form.whatsapp_payment_enabled} onChange={v=>toggle("whatsapp_payment_enabled",v)}/>
          <Toggle compact title="Rappels de live" checked={form.whatsapp_live_enabled} onChange={v=>toggle("whatsapp_live_enabled",v)}/>
          <Toggle compact title="Reprendre un cours" checked={form.whatsapp_inactivity_enabled} onChange={v=>toggle("whatsapp_inactivity_enabled",v)}/>
          <Toggle compact title="Certificats disponibles" checked={form.whatsapp_certificate_enabled} onChange={v=>toggle("whatsapp_certificate_enabled",v)}/>
        </div>}
        {form.whatsapp_consent_at && form.whatsapp_opt_in && <p className="flex items-center gap-1 text-[11px] text-emerald-700"><CheckCircle2 size={13}/> Consentement enregistré.</p>}
        {error && <p className="text-xs text-red-600">{error}</p>}{message && <p className="text-xs text-emerald-700">{message}</p>}
        <button type="button" onClick={save} disabled={saving} className="btn-primary w-full sm:w-auto">{saving?<Loader2 className="animate-spin" size={15}/>:<Save size={15}/>} Enregistrer WhatsApp</button>
      </div>
    </section>
  );
}

function Toggle({title,description,checked,onChange,compact=false}:{title:string;description?:string;checked:boolean;onChange:(v:boolean)=>void;compact?:boolean}){
  return <label className={`flex cursor-pointer items-center justify-between gap-3 ${compact?"rounded-lg bg-white px-3 py-2":"rounded-xl border border-gray-100 px-3 py-3"}`}><span><span className="block text-sm font-semibold">{title}</span>{description&&<span className="mt-0.5 block text-[11px] text-gray-400">{description}</span>}</span><input type="checkbox" checked={checked} onChange={e=>onChange(e.target.checked)} className="h-4 w-4 accent-emerald-600"/></label>
}
