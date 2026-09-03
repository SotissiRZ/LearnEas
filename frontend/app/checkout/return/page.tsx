"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { CheckCircle2, Loader2, RotateCcw, XCircle } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useCart } from "@/hooks/useCart";

type State = "checking" | "paid" | "waiting" | "failed";
type ConfirmedOrder = { items?: Array<{ item_type?: string }> };

export default function CheckoutReturnPage() {
  const router = useRouter();
  const params = useSearchParams();
  const clear = useCart((state) => state.clear);
  const orderId = Number(params.get("order") || 0);
  const [state, setState] = useState<State>("checking");
  const [message, setMessage] = useState("Vérification de votre paiement Mobile Money…");
  const attemptRef = useRef(0);

  useEffect(() => {
    if (!orderId) {
      setState("failed");
      setMessage("Référence de commande manquante.");
      return;
    }

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const check = async () => {
      attemptRef.current += 1;
      setState(attemptRef.current === 1 ? "checking" : "waiting");
      try {
        const order = await api.post<ConfirmedOrder>(`/payments/orders/${orderId}/confirm/`, {});
        if (cancelled) return;
        clear();
        setState("paid");
        setMessage("Paiement confirmé. Votre accès est activé.");
        const items = order.items || [];
        const mentorshipOnly = items.length > 0 && items.every((item) => item.item_type === "mentoring");
        const destination = mentorshipOnly
          ? `/dashboard/student/mentorship?booked=1&order=${orderId}`
          : `/dashboard/student?purchased=1&order=${orderId}`;
        timer = setTimeout(() => router.replace(destination), 900);
      } catch (error) {
        if (cancelled) return;
        const text = error instanceof ApiError ? error.message : "Impossible de vérifier le paiement.";
        const refused = /refus|annul|failed/i.test(text);
        if (refused) {
          setState("failed");
          setMessage(text);
          return;
        }
        if (attemptRef.current < 12) {
          setState("waiting");
          setMessage("Paiement reçu, confirmation opérateur en cours…");
          timer = setTimeout(check, 2000);
        } else {
          setState("waiting");
          setMessage("La confirmation prend plus de temps que prévu. Votre commande sera activée automatiquement dès réception du webhook opérateur.");
        }
      }
    };

    check();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [orderId, clear, router]);

  return (
    <div className="container-app flex min-h-[65vh] items-center justify-center py-12">
      <div className="card w-full max-w-lg p-7 text-center">
        <div className="mx-auto mb-4 grid h-14 w-14 place-items-center rounded-full bg-brand-50 text-brand-700">
          {state === "paid" ? <CheckCircle2 size={30} /> : state === "failed" ? <XCircle size={30} className="text-red-600" /> : <Loader2 size={28} className="animate-spin" />}
        </div>
        <h1 className="text-xl font-extrabold">
          {state === "paid" ? "Paiement confirmé" : state === "failed" ? "Paiement non confirmé" : "Confirmation Mobile Money"}
        </h1>
        <p className="mt-3 text-sm leading-6 text-gray-600">{message}</p>
        <p className="mt-2 text-xs text-gray-400">Commande #{orderId || "—"}</p>
        {state === "failed" && (
          <button type="button" onClick={() => router.replace("/checkout")} className="btn-primary mt-6 w-full">
            <RotateCcw size={17} /> Réessayer le paiement
          </button>
        )}
        {state === "waiting" && attemptRef.current >= 12 && (
          <button type="button" onClick={() => window.location.reload()} className="btn-outline mt-6 w-full">
            <RotateCcw size={17} /> Vérifier à nouveau
          </button>
        )}
      </div>
    </div>
  );
}
