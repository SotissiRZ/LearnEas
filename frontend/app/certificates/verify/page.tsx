"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Search, ShieldCheck } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { Certificate } from "@/types";

export default function VerifyLanding() {
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  async function submit(event: FormEvent) {
    event.preventDefault();
    const value = query.trim();
    if (!value) return;
    setLoading(true);
    setError("");
    try {
      const certificate = await api.get<Certificate>(`/enrollments/certificates/lookup/?q=${encodeURIComponent(value)}`);
      router.push(`/certificates/verify/${certificate.verification_code}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Certificat introuvable.");
    } finally {
      setLoading(false);
    }
  }

  return <div className="container-app max-w-xl py-16">
    <div className="card p-8 text-center">
      <ShieldCheck className="mx-auto text-brand-600" size={38}/>
      <h1 className="mt-3 text-2xl font-bold">Vérifier un certificat</h1>
      <p className="mt-2 text-sm text-gray-500">Saisissez le numéro du certificat ou son code de vérification. Vous pouvez aussi scanner directement le QR code imprimé sur le certificat.</p>
      <form className="mt-6 space-y-3" onSubmit={submit}>
        <label className="relative block text-left">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"/>
          <input className="input-admin w-full pl-9" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Ex. LE-CERT-2026-… ou code UUID" autoComplete="off"/>
        </label>
        {error && <p className="text-left text-sm text-red-600">{error}</p>}
        <button disabled={loading || !query.trim()} className="btn-primary w-full justify-center disabled:opacity-50">{loading && <Loader2 size={15} className="animate-spin"/>} Vérifier dans le registre</button>
      </form>
      <p className="mt-5 text-xs leading-5 text-gray-400">Le registre public confirme l'état actuel du certificat. Un ancien certificat révoqué ou expiré reste consultable afin que son historique ne puisse pas être effacé.</p>
    </div>
  </div>;
}
