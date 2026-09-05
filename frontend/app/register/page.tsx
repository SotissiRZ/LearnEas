"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { Loader2, AlertCircle, CheckCircle2, GraduationCap, Building2 } from "lucide-react";
import BrandLogo from "@/components/layout/BrandLogo";
import { useAuth } from "@/hooks/useAuth";
import { ApiError } from "@/lib/api";
import PasswordInput from "@/components/ui/PasswordInput";
import CountrySelect from "@/components/ui/CountrySelect";

type PublicRole = "student" | "employer";

export default function RegisterPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const register = useAuth((s) => s.register);
  const [form, setForm] = useState({
    role: "student" as PublicRole,
    email: "", first_name: "", last_name: "", country: "",
    company_name: "", industry: "", company_size: "", website_url: "", city: "",
    password: "", password2: "",
  });
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});
  const [globalError, setGlobalError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const invitedEmail = searchParams.get("email")?.trim().toLowerCase();
    const requestedRole = searchParams.get("role") === "employer" ? "employer" : "student";
    setForm((current) => ({ ...current, ...(invitedEmail ? { email: invitedEmail } : {}), role: requestedRole }));
  }, [searchParams]);

  function set(key: string, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
    setFieldErrors((fe) => ({ ...fe, [key]: [] }));
  }

  function validateClientSide(): boolean {
    const errors: Record<string, string[]> = {};
    if (!/^\S+@\S+\.\S+$/.test(form.email)) errors.email = ["Adresse email invalide."];
    if (!form.country) errors.country = ["Sélectionnez votre pays."];
    if (form.role === "employer" && !form.company_name.trim()) errors.company_name = ["Indiquez le nom de l’entreprise."];
    if (form.password.length < 8) errors.password = ["Doit contenir au moins 8 caractères."];
    if (form.password !== form.password2) errors.password2 = ["Les mots de passe ne correspondent pas."];
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setGlobalError("");
    if (!validateClientSide()) return;
    setLoading(true);
    try {
      const user = await register(form);
      const next = searchParams.get("next");
      let safeNext = user.role === "employer" ? "/dashboard/employer" : "/dashboard/student";
      if (next && next.startsWith("/") && !next.startsWith("//")) {
        try {
          const target = new URL(next, window.location.origin);
          if (target.origin === window.location.origin) safeNext = `${target.pathname}${target.search}${target.hash}`;
        } catch { /* conserver la destination liée au rôle */ }
      }
      router.push(safeNext);
    } catch (err) {
      if (err instanceof ApiError) {
        setFieldErrors(err.fieldErrors);
        const hasFieldMatch = Object.keys(err.fieldErrors).some((k) => k in form);
        setGlobalError(hasFieldMatch ? "" : err.message);
      } else setGlobalError("Une erreur inattendue est survenue. Veuillez réessayer.");
    } finally { setLoading(false); }
  }

  function fieldError(name: string) {
    const msgs = fieldErrors[name];
    if (!msgs?.length) return null;
    return <p className="mt-1 flex items-center gap-1 text-xs text-red-600"><AlertCircle size={12} /> {msgs[0]}</p>;
  }

  return (
    <div className="relative flex min-h-[calc(100vh-72px)] items-center justify-center overflow-hidden bg-navy-950 px-4 py-10">
      <div className="absolute inset-0 bg-hero-radial" />
      <div className="relative w-full max-w-2xl rounded-3xl border border-white/10 bg-white p-5 shadow-2xl sm:p-8">
        <div className="mb-6 flex flex-col items-center gap-3 text-center">
          <div className="rounded-2xl bg-navy-950 px-4 py-3"><BrandLogo /></div>
          <div><h1 className="text-2xl font-black text-navy-950">Créer un compte</h1><p className="mt-1 text-sm text-slate-500">Choisissez votre espace KalanPro</p></div>
        </div>

        <div className="mb-6 grid gap-3 sm:grid-cols-2">
          <RoleCard active={form.role === "student"} onClick={() => set("role", "student")} icon={<GraduationCap size={20} />} title="Je veux apprendre" text="Cours, cohortes, projets, portfolio et opportunités." />
          <RoleCard active={form.role === "employer"} onClick={() => set("role", "employer")} icon={<Building2 size={20} />} title="Je recrute" text="Profil entreprise, offres, candidatures et vivier de talents." />
        </div>

        {globalError && <div className="mb-4 flex items-start gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700"><AlertCircle size={16} className="mt-0.5 shrink-0" /> {globalError}</div>}

        <form onSubmit={handleSubmit} noValidate className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div><input autoComplete="given-name" placeholder="Prénom" value={form.first_name} onChange={(e) => set("first_name", e.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-100" /></div>
          <div><input autoComplete="family-name" placeholder="Nom" value={form.last_name} onChange={(e) => set("last_name", e.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-100" /></div>
          <div className="sm:col-span-2"><input required type="email" inputMode="email" autoComplete="email" placeholder="Email" value={form.email} onChange={(e) => set("email", e.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-100" />{fieldError("email")}</div>
          <div className="sm:col-span-2"><CountrySelect required value={form.country} onChange={(country) => set("country", country)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-100" />{fieldError("country")}</div>

          {form.role === "employer" && <>
            <div className="sm:col-span-2"><input required placeholder="Nom de l’entreprise *" value={form.company_name} onChange={(e) => set("company_name", e.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-100" />{fieldError("company_name")}</div>
            <div><input placeholder="Secteur (ex. FinTech, ONG...)" value={form.industry} onChange={(e) => set("industry", e.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm" /></div>
            <div><select value={form.company_size} onChange={(e) => set("company_size", e.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm"><option value="">Taille de l’entreprise</option><option value="solo">Indépendant</option><option value="1-10">1–10</option><option value="11-50">11–50</option><option value="51-200">51–200</option><option value="201-1000">201–1000</option><option value="1000+">1000+</option></select></div>
            <div><input placeholder="Ville" value={form.city} onChange={(e) => set("city", e.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm" /></div>
            <div><input type="url" placeholder="Site web (optionnel)" value={form.website_url} onChange={(e) => set("website_url", e.target.value)} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm" /></div>
            <p className="sm:col-span-2 rounded-xl bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-800">Votre espace entreprise est créé immédiatement. La publication d’offres et l’accès au vivier de talents sont activés après validation par KalanPro.</p>
          </>}

          <div><PasswordInput required placeholder="Mot de passe (8 caractères min.)" value={form.password} onChange={(e: any) => set("password", e.target.value)} showIcon={false} className="w-full rounded-lg border border-slate-200 py-2.5 pl-3 pr-10 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-100" />{fieldError("password")}</div>
          <div><PasswordInput required placeholder="Confirmer le mot de passe" value={form.password2} onChange={(e: any) => set("password2", e.target.value)} showIcon={false} className="w-full rounded-lg border border-slate-200 py-2.5 pl-3 pr-10 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-100" />{fieldError("password2")}</div>

          <button type="submit" disabled={loading} className="btn-primary sm:col-span-2">{loading ? <Loader2 className="animate-spin" size={18} /> : <CheckCircle2 size={18} />}{form.role === "employer" ? "Créer mon espace entreprise" : "Créer mon compte"}</button>
        </form>

        <p className="mt-6 text-center text-sm text-slate-500">Déjà inscrit ? <Link href="/login" className="font-semibold text-brand-700">Connectez-vous</Link></p>
        <p className="mt-2 text-center text-xs text-slate-400">Vous souhaitez enseigner ? Créez d’abord un compte apprenant puis utilisez « Devenir instructeur » pour la vérification du profil.</p>
      </div>
    </div>
  );
}

function RoleCard({ active, onClick, icon, title, text }: { active: boolean; onClick: () => void; icon: React.ReactNode; title: string; text: string }) {
  return <button type="button" onClick={onClick} className={`flex items-start gap-3 rounded-2xl border p-4 text-left transition ${active ? "border-brand-500 bg-brand-50 ring-2 ring-brand-100" : "border-slate-200 hover:border-slate-300"}`}><span className={`grid h-10 w-10 shrink-0 place-items-center rounded-xl ${active ? "bg-brand-500 text-white" : "bg-slate-100 text-slate-600"}`}>{icon}</span><span><span className="block font-bold text-navy-950">{title}</span><span className="mt-1 block text-xs leading-5 text-slate-500">{text}</span></span></button>;
}
