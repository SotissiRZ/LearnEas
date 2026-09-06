"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Crown, Loader2 } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";

type PremiumStatus = {
  active: boolean;
  starts_at: string | null;
  current_period_ends_at: string | null;
  coverage_ends_at: string | null;
};

export default function PremiumAccessAction({
  kind,
  id,
  available,
  destination,
}: {
  kind: "course" | "pdf";
  id: number;
  available?: boolean;
  destination?: string;
}) {
  const { user } = useAuth();
  const router = useRouter();
  const [status, setStatus] = useState<PremiumStatus | null>(null);
  const [checking, setChecking] = useState(Boolean(available && user));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!available || !user) { setChecking(false); return; }
    setChecking(true);
    api.get<PremiumStatus>("/payments/premium/")
      .then(setStatus)
      .catch(() => setStatus(null))
      .finally(() => setChecking(false));
  }, [available, user]);

  if (!available) return null;

  if (checking) {
    return <button type="button" disabled className="btn-outline mt-2 w-full opacity-70"><Loader2 size={17} className="animate-spin" /> Vérification Premium…</button>;
  }

  if (!user || !status?.active) {
    return (
      <Link href="/pricing#apprenants" className="btn-outline mt-2 w-full">
        <Crown size={17} /> Disponible avec Premium
      </Link>
    );
  }

  async function claim() {
    setLoading(true);
    setError("");
    try {
      await api.post("/payments/premium/", kind === "course" ? { course_id: id } : { pdf_id: id });
      if (destination) {
        router.push(destination);
        router.refresh();
      } else {
        window.location.reload();
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Impossible d'activer l'accès Premium.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mt-2">
      <button type="button" onClick={claim} disabled={loading} className="btn-outline w-full">
        {loading ? <Loader2 size={17} className="animate-spin" /> : <Crown size={17} />}
        Accéder avec Premium
      </button>
      {status.coverage_ends_at && (
        <p className="mt-1 text-center text-[11px] text-gray-400">
          Pass actif jusqu'au {new Date(status.coverage_ends_at).toLocaleDateString("fr-FR")}
        </p>
      )}
      {error && <p className="mt-1 text-center text-xs text-red-600">{error}</p>}
    </div>
  );
}
