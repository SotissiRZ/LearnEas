"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { GraduationCap, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { ApiError } from "@/lib/api";
import PasswordInput from "@/components/ui/PasswordInput";

const AFRICAN_COUNTRIES = [
  "Maroc", "Sénégal", "Côte d'Ivoire", "Cameroun", "Mali", "Burkina Faso", "Bénin",
  "Togo", "Niger", "Guinée", "RD Congo", "Congo", "Gabon", "Tchad", "Rwanda",
  "Kenya", "Nigeria", "Ghana", "Tunisie", "Algérie", "Égypte", "Madagascar",
  "Mauritanie", "République centrafricaine", "Burundi", "Autre",
];

export default function RegisterPage() {
  const router = useRouter();
  const register = useAuth((s) => s.register);
  const [form, setForm] = useState({
    email: "", first_name: "", last_name: "", country: "",
    password: "", password2: "",
  });
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});
  const [globalError, setGlobalError] = useState("");
  const [loading, setLoading] = useState(false);

  function set(key: string, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
    setFieldErrors((fe) => ({ ...fe, [key]: [] }));
  }

  function validateClientSide(): boolean {
    const errors: Record<string, string[]> = {};
    if (!/^\S+@\S+\.\S+$/.test(form.email)) {
      errors.email = ["Adresse email invalide."];
    }
    if (form.password.length < 8) {
      errors.password = ["Doit contenir au moins 8 caractères."];
    }
    if (form.password !== form.password2) {
      errors.password2 = ["Les mots de passe ne correspondent pas."];
    }
    setFieldErrors(errors);
    return Object.keys(errors).length === 0;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setGlobalError("");
    if (!validateClientSide()) return;

    setLoading(true);
    try {
      await register(form);
      router.push("/dashboard/student");
    } catch (err) {
      if (err instanceof ApiError) {
        setFieldErrors(err.fieldErrors);
        // Si l'erreur ne cible aucun champ connu (ex: erreur réseau/serveur), on l'affiche en global.
        const hasFieldMatch = Object.keys(err.fieldErrors).some((k) => k in form);
        setGlobalError(hasFieldMatch ? "" : err.message);
      } else {
        setGlobalError("Une erreur inattendue est survenue. Veuillez réessayer.");
      }
    } finally {
      setLoading(false);
    }
  }

  function fieldError(name: string) {
    const msgs = fieldErrors[name];
    if (!msgs || msgs.length === 0) return null;
    return <p className="mt-1 flex items-center gap-1 text-xs text-red-600"><AlertCircle size={12} /> {msgs[0]}</p>;
  }

  return (
    <div className="container-app flex min-h-[70vh] items-center justify-center py-8 sm:py-16">
      <div className="card w-full max-w-lg p-4 sm:p-8">
        <div className="mb-6 flex flex-col items-center gap-2">
          <div className="grid h-12 w-12 place-items-center rounded-2xl bg-brand-600 text-white">
            <GraduationCap size={24} />
          </div>
          <h1 className="text-2xl font-extrabold">Créer un compte</h1>
          <p className="text-sm text-gray-500">Rejoignez LearnEas gratuitement, partout en Afrique</p>
        </div>

        {globalError && (
          <div className="mb-4 flex items-start gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
            <AlertCircle size={16} className="mt-0.5 shrink-0" /> {globalError}
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <input autoComplete="given-name" placeholder="Prénom" value={form.first_name} onChange={(e) => set("first_name", e.target.value)}
              className="w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-100" />
          </div>
          <div>
            <input autoComplete="family-name" placeholder="Nom" value={form.last_name} onChange={(e) => set("last_name", e.target.value)}
              className="w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-100" />
          </div>
          <div className="sm:col-span-2">
            <input required type="email" inputMode="email" autoComplete="email" placeholder="Email" value={form.email} onChange={(e) => set("email", e.target.value)}
              className="w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-100" />
            {fieldError("email")}
          </div>
          <div className="sm:col-span-2">
            <select value={form.country} onChange={(e) => set("country", e.target.value)}
              className="w-full rounded-lg border border-gray-200 px-3 py-2.5 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-100">
              <option value="">Sélectionnez votre pays</option>
              {AFRICAN_COUNTRIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>
          <div>
            <PasswordInput required placeholder="Mot de passe (8 caractères min.)" value={form.password}
              onChange={(e: any) => set("password", e.target.value)} showIcon={false}
              className="w-full rounded-lg border border-gray-200 py-2.5 pl-3 pr-10 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-100" />
            {fieldError("password")}
          </div>
          <div>
            <PasswordInput required placeholder="Confirmer le mot de passe" value={form.password2}
              onChange={(e: any) => set("password2", e.target.value)} showIcon={false}
              className="w-full rounded-lg border border-gray-200 py-2.5 pl-3 pr-10 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-100" />
            {fieldError("password2")}
          </div>

          <button type="submit" disabled={loading} className="btn-primary sm:col-span-2">
            {loading ? <Loader2 className="animate-spin" size={18} /> : <CheckCircle2 size={18} />}
            Créer mon compte
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-500">
          Déjà inscrit ? <Link href="/login" className="font-semibold text-brand-700">Connectez-vous</Link>
        </p>
      </div>
    </div>
  );
}
