"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { GraduationCap, Loader2 } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

export default function RegisterPage() {
  const router = useRouter();
  const register = useAuth((s) => s.register);
  const [form, setForm] = useState({
    username: "", email: "", first_name: "", last_name: "", country: "",
    password: "", password2: "",
  });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  function set(key: string, value: string) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await register(form);
      router.push("/dashboard/student");
    } catch (err: any) {
      setError(err.message || "Impossible de créer le compte.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container-app flex min-h-[70vh] items-center justify-center py-16">
      <div className="card w-full max-w-lg p-8">
        <div className="mb-6 flex flex-col items-center gap-2">
          <div className="grid h-12 w-12 place-items-center rounded-2xl bg-brand-600 text-white">
            <GraduationCap size={24} />
          </div>
          <h1 className="text-2xl font-extrabold">Créer un compte</h1>
          <p className="text-sm text-gray-500">Rejoignez LearnEas gratuitement</p>
        </div>

        <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <input required placeholder="Prénom" value={form.first_name} onChange={(e) => set("first_name", e.target.value)}
            className="rounded-lg border border-gray-200 px-3 py-2.5 text-sm sm:col-span-1" />
          <input required placeholder="Nom" value={form.last_name} onChange={(e) => set("last_name", e.target.value)}
            className="rounded-lg border border-gray-200 px-3 py-2.5 text-sm sm:col-span-1" />
          <input required placeholder="Nom d'utilisateur" value={form.username} onChange={(e) => set("username", e.target.value)}
            className="rounded-lg border border-gray-200 px-3 py-2.5 text-sm sm:col-span-2" />
          <input required type="email" placeholder="Email" value={form.email} onChange={(e) => set("email", e.target.value)}
            className="rounded-lg border border-gray-200 px-3 py-2.5 text-sm sm:col-span-2" />
          <input placeholder="Pays" value={form.country} onChange={(e) => set("country", e.target.value)}
            className="rounded-lg border border-gray-200 px-3 py-2.5 text-sm sm:col-span-2" />
          <input required type="password" placeholder="Mot de passe" value={form.password} onChange={(e) => set("password", e.target.value)}
            className="rounded-lg border border-gray-200 px-3 py-2.5 text-sm sm:col-span-1" />
          <input required type="password" placeholder="Confirmer" value={form.password2} onChange={(e) => set("password2", e.target.value)}
            className="rounded-lg border border-gray-200 px-3 py-2.5 text-sm sm:col-span-1" />

          {error && <p className="text-sm text-red-600 sm:col-span-2">{error}</p>}

          <button type="submit" disabled={loading} className="btn-primary sm:col-span-2">
            {loading && <Loader2 className="animate-spin" size={18} />}
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
