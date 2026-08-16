"use client";

import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { GraduationCap, Loader2, Mail, AlertCircle } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { ApiError } from "@/lib/api";
import PasswordInput from "@/components/ui/PasswordInput";

export default function LoginPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const login = useAuth((s) => s.login);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const user = await login(email, password);
      const next = searchParams.get("next");
      if (next) router.push(next);
      else if (user.role === "admin") router.push("/dashboard/admin");
      else if (user.role === "instructor") router.push("/dashboard/instructor");
      else router.push("/dashboard/student");
    } catch (err) {
      if (err instanceof ApiError) {
        setError("Email ou mot de passe incorrect.");
      } else {
        setError("Une erreur inattendue est survenue. Veuillez réessayer.");
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
          <h1 className="text-2xl font-extrabold">Content de vous revoir</h1>
          <p className="text-sm text-gray-500">Connectez-vous à votre compte LearnEas</p>
        </div>

        <form onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
          <div>
            <label className="mb-1 block text-sm font-medium">Email</label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
              <input
                type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-lg border border-gray-200 py-2.5 pl-10 pr-3 text-sm focus:border-brand-500 focus:ring-2 focus:ring-brand-100"
                placeholder="vous@exemple.com"
              />
            </div>
          </div>
          <div>
            <div className="mb-1 flex items-center justify-between">
              <label className="block text-sm font-medium">Mot de passe</label>
              <Link href="/forgot-password" className="text-xs font-semibold text-brand-700">
                Mot de passe oublié ?
              </Link>
            </div>
            <PasswordInput required value={password} onChange={(e: any) => setPassword(e.target.value)} placeholder="••••••••" />
          </div>

          {error && (
            <div className="flex items-start gap-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">
              <AlertCircle size={16} className="mt-0.5 shrink-0" /> {error}
            </div>
          )}

          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading && <Loader2 className="animate-spin" size={18} />}
            Se connecter
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-gray-500">
          Pas encore de compte ? <Link href="/register" className="font-semibold text-brand-700">Inscrivez-vous</Link>
        </p>
      </div>
    </div>
  );
}
