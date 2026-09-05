"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { CheckCircle2, Loader2, RotateCcw, XCircle } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useCart } from "@/hooks/useCart";

type State = "checking" | "paid" | "waiting" | "failed";
type ConfirmedOrder = {
  id: number;
  status: "pending" | "paid" | "failed" | "refunded" | string;
  provider_status?: string;
  payment_method?: string;
  items?: Array<{ item_type?: string }>;
};

export default function CheckoutReturnPage() {
  const router = useRouter();
  const params = useSearchParams();
  const clear = useCart((state) => state.clear);
  const orderId = Number(params.get("order") || 0);
  const [state, setState] = useState<State>("checking");
  const [message, setMessage] = useState("Vérification de votre paiement Mobile Money…");
  const pollRef = useRef(0);
  const providerCheckRef = useRef(0);

  useEffect(() => {
    if (!orderId) {
      setState("failed");
      setMessage("Référence de commande manquante.");
      return;
    }

    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    const finishPaid = (order: ConfirmedOrder) => {
      clear();
      setState("paid");
      const method = order.payment_method ? ` via ${order.payment_method}` : "";
      setMessage(`Paiement confirmé${method}. Votre accès est activé.`);
      const items = order.items || [];
      const employerOnly = items.length > 0 && items.every((item) => item.item_type === "employer");
      const mentorshipOnly = items.length > 0 && items.every((item) => item.item_type === "mentoring");
      const destination = employerOnly
        ? `/dashboard/employer?billing=updated&order=${orderId}`
        : mentorshipOnly
          ? `/dashboard/student/mentorship?booked=1&order=${orderId}`
          : `/dashboard/student?purchased=1&order=${orderId}`;
      timer = setTimeout(() => router.replace(destination), 900);
    };

    const schedule = (fn: () => void) => {
      const delay = Math.min(3000 + pollRef.current * 750, 8000);
      timer = setTimeout(fn, delay);
    };

    const handleOrder = (order: ConfirmedOrder) => {
      if (cancelled) return true;
      if (order.status === "paid") {
        finishPaid(order);
        return true;
      }
      if (order.status === "failed" || order.status === "refunded") {
        setState("failed");
        setMessage(order.status === "refunded" ? "Cette commande a été remboursée." : "Le paiement a échoué ou a été annulé.");
        return true;
      }
      setState("waiting");
      const providerStatus = order.provider_status ? ` (${order.provider_status})` : "";
      setMessage(`Confirmation opérateur en cours${providerStatus}…`);
      return false;
    };

    const pollInternalStatus = async () => {
      pollRef.current += 1;
      try {
        const order = await api.get<ConfirmedOrder>(`/payments/orders/${orderId}/`);
        if (handleOrder(order)) return;
      } catch (error) {
        if (cancelled) return;
        const text = error instanceof ApiError ? error.message : "Impossible de vérifier la commande.";
        setState("waiting");
        setMessage(`${text} Nouvelle tentative automatique…`);
      }

      if (pollRef.current >= 12) {
        setState("waiting");
        setMessage("La confirmation prend plus de temps que prévu. KalanPro continuera la réconciliation automatiquement en arrière-plan.");
        return;
      }

      // Trois contrôles prestataire maximum pendant la page de retour. Entre eux, on lit
      // uniquement l'état KalanPro actualisé par les webhooks, ce qui évite de marteler le wallet.
      if ([3, 7].includes(pollRef.current)) {
        schedule(confirmWithProvider);
      } else {
        schedule(pollInternalStatus);
      }
    };

    const confirmWithProvider = async () => {
      providerCheckRef.current += 1;
      setState(providerCheckRef.current === 1 ? "checking" : "waiting");
      try {
        const order = await api.post<ConfirmedOrder>(`/payments/orders/${orderId}/confirm/`, {});
        if (handleOrder(order)) return;
      } catch (error) {
        if (cancelled) return;
        const text = error instanceof ApiError ? error.message : "Impossible de vérifier le paiement.";
        const refused = /refus|annul|failed|rembours/i.test(text);
        if (refused) {
          setState("failed");
          setMessage(text);
          return;
        }
        setState("waiting");
        setMessage("Paiement initié, confirmation opérateur en cours…");
      }
      schedule(pollInternalStatus);
    };

    void confirmWithProvider();
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
        {state === "waiting" && pollRef.current >= 12 && (
          <button type="button" onClick={() => window.location.reload()} className="btn-outline mt-6 w-full">
            <RotateCcw size={17} /> Vérifier à nouveau
          </button>
        )}
      </div>
    </div>
  );
}
