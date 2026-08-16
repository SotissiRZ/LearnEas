"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { GraduationCap, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import PasswordInput from "@/components/ui/PasswordInput";

export default function ResetPasswordPage() {
  const params = useParams<{ uid: string; token: string }>();
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [password2, setPassword2] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("Le mot de passe doit contenir au moins 8 caractères.");
      return;
    }
    if (password !== password2) {
      setError("Les mots de passe ne correspondent pas.");
      return;
    }

    setLoading(true);
    try {
      await api.post("/auth/password-reset-confirm/", {
        uid: params.uid,
        token: params.token,
        new_password: password,
        new_password2: password2,
      });
      setSuccess(true);
      setTimeout(() => router.push("/login"), 2000);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Ce lien est invalide ou a expiré. Refaites une demande de réinitialisation.");
      }
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
          <h1 className="text-2xl font-extrabold">Nouveau mot de passe</h1>
          <p className="text-center text-sm text-gray-500">Choisissez un nouveau mot de passe pour votre compte.</p>
        </div>

        {success ? (
          <div className="flex flex-col items-center gap-2 rounded-lg bg-brand-50 p-4 text-center text-sm text-brand-800">
            <CheckCircle2 size={28} className="text-brand-600" />
            Mot de passe modifié avec succès. Redirection vers la connexion...
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium">Nouveau mot de passe</label>
              <PasswordInput required value={password} onChange={(e: any) => setPassword(e.target.value)} placeholder="8 caractères minimum" />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium">Confirmer le mot de passe</label>
              <PasswordInput required value={password2} onChange={(e: any) => setPassword2(e.target.value)} placeholder="••••••••" />
            </div>

            {error && (
              <div className="flex items-start gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
                <AlertCircle size={16} className="mt-0.5 shrink-0" /> {error}
              </div>
            )}

            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading && <Loader2 className="animate-spin" size={18} />}
              Réinitialiser le mot de passe
            </button>
          </form>
        )}

        <Link href="/login" className="mt-6 block text-center text-sm font-semibold text-brand-700">
          Retour à la connexion
        </Link>
      </div>
    </div>
  );
}
