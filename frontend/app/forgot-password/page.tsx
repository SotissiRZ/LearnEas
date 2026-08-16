"use client";

import { useState } from "react";
import Link from "next/link";
import { GraduationCap, Loader2, Mail, ArrowLeft, CheckCircle2 } from "lucide-react";
import { api } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [devUrl, setDevUrl] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await api.post<{ detail: string; dev_reset_url?: string }>("/auth/password-reset/", { email });
      setSent(true);
      if (res.dev_reset_url) setDevUrl(res.dev_reset_url);
    } catch {
      // Par sécurité, on affiche toujours le même message de succès (ne jamais confirmer
      // ou infirmer l'existence d'un compte).
      setSent(true);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container-app flex min-h-[70vh] items-center justify-center py-16">
      <div className="card w-full max-w-md p-8">
        <div className="mb-6 flex flex-col items-center gap-2">
          <div className="grid h-12 w-12 place-items-center rounded-2xl bg-brand-600 text-white">
            <GraduationCap size={24} />
          </div>
          <h1 className="text-2xl font-extrabold">Mot de passe oublié ?</h1>
          <p className="text-center text-sm text-gray-500">
            Indiquez votre email, nous vous envoyons un lien pour le réinitialiser.
          </p>
        </div>

        {sent ? (
          <div className="flex flex-col items-center gap-3 rounded-lg bg-brand-50 p-4 text-center text-sm text-brand-800">
            <CheckCircle2 size={28} className="text-brand-600" />
            <p>Si un compte existe avec cet email, un lien de réinitialisation vient d'être envoyé.</p>
            {devUrl && (
              <div className="mt-2 w-full rounded-lg bg-white p-3 text-left">
                <p className="mb-1 text-xs font-semibold text-gray-500">
                  Mode développement — pas de serveur email configuré, voici le lien direct :
                </p>
                <Link href={devUrl.replace(/^https?:\/\/[^/]+/, "")} className="break-all text-xs text-brand-700 underline">
                  {devUrl}
                </Link>
              </div>
            )}
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
              <input
                type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-gray-200 py-2.5 pl-10 pr-3 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                placeholder="vous@exemple.com"
              />
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading && <Loader2 className="animate-spin" size={18} />}
              Envoyer le lien de réinitialisation
            </button>
          </form>
        )}

        <Link href="/login" className="mt-6 flex items-center justify-center gap-1 text-sm font-semibold text-brand-700">
          <ArrowLeft size={14} /> Retour à la connexion
        </Link>
      </div>
    </div>
  );
}
