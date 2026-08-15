"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { CreditCard, Loader2, ShieldCheck } from "lucide-react";
import { useCart } from "@/hooks/useCart";
import { useAuth } from "@/hooks/useAuth";
import { api, formatPrice } from "@/lib/api";

export default function CheckoutPage() {
  const { items, total, clear } = useCart();
  const { user } = useAuth();
  const router = useRouter();
  const [provider, setProvider] = useState<"stripe" | "paypal">("stripe");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handlePay() {
    setLoading(true);
    setError("");
    try {
      const course_ids = items.filter((i) => i.type === "course").map((i) => i.id);
      const pdf_ids = items.filter((i) => i.type === "pdf").map((i) => i.id);

      const res = await api.post<{ order: { id: number }; requires_payment: boolean }>(
        "/payments/checkout/",
        { course_ids, pdf_ids, provider }
      );

      if (res.requires_payment) {
        // En production : redirection vers Stripe Checkout / PayPal.
        // Ici on confirme directement pour la démo (webhook simulé).
        await api.post(`/payments/orders/${res.order.id}/confirm/`);
      }

      clear();
      router.push("/dashboard/student?purchased=1");
    } catch (e: any) {
      setError(e.message || "Une erreur est survenue lors du paiement.");
    } finally {
      setLoading(false);
    }
  }

  if (!user) {
    return <div className="container-app py-20 text-center text-gray-500">Veuillez vous connecter pour continuer.</div>;
  }

  if (items.length === 0) {
    return <div className="container-app py-20 text-center text-gray-500">Votre panier est vide.</div>;
  }

  return (
    <div className="container-app grid grid-cols-1 gap-8 py-10 lg:grid-cols-[1fr_380px]">
      <div>
        <h1 className="mb-6 text-2xl font-extrabold">Paiement</h1>

        <div className="card p-5">
          <h2 className="mb-3 font-semibold">Mode de paiement</h2>
          <div className="grid grid-cols-2 gap-3">
            <button
              onClick={() => setProvider("stripe")}
              className={`rounded-xl border p-4 text-left ${provider === "stripe" ? "border-brand-600 bg-brand-50" : "border-gray-200"}`}
            >
              <CreditCard className="mb-2" />
              <p className="font-semibold">Carte bancaire</p>
              <p className="text-xs text-gray-500">Visa, Mastercard, Maestro</p>
            </button>
            <button
              onClick={() => setProvider("paypal")}
              className={`rounded-xl border p-4 text-left ${provider === "paypal" ? "border-brand-600 bg-brand-50" : "border-gray-200"}`}
            >
              <p className="mb-2 text-xl font-black text-blue-700">PayPal</p>
              <p className="text-xs text-gray-500">Payer avec votre compte PayPal</p>
            </button>
          </div>

          {provider === "stripe" && (
            <div className="mt-5 grid grid-cols-2 gap-3">
              <input placeholder="Numéro de carte" className="col-span-2 rounded-lg border border-gray-200 px-3 py-2 text-sm" />
              <input placeholder="MM / AA" className="rounded-lg border border-gray-200 px-3 py-2 text-sm" />
              <input placeholder="CVC" className="rounded-lg border border-gray-200 px-3 py-2 text-sm" />
            </div>
          )}

          {error && <p className="mt-3 text-sm text-red-600">{error}</p>}

          <button onClick={handlePay} disabled={loading} className="btn-primary mt-5 w-full">
            {loading ? <Loader2 className="animate-spin" size={18} /> : <ShieldCheck size={18} />}
            Payer {formatPrice(total())}
          </button>
          <p className="mt-2 text-center text-xs text-gray-400">Paiement chiffré et sécurisé.</p>
        </div>
      </div>

      <div className="card h-fit p-5">
        <h2 className="mb-4 font-bold">Récapitulatif</h2>
        <div className="flex flex-col gap-2 text-sm">
          {items.map((item) => (
            <div key={`${item.type}-${item.id}`} className="flex justify-between">
              <span className="line-clamp-1">{item.title}</span>
              <span className="font-semibold">{formatPrice(item.price)}</span>
            </div>
          ))}
        </div>
        <div className="mt-4 flex items-center justify-between border-t border-gray-100 pt-4 text-lg font-extrabold">
          <span>Total</span>
          <span>{formatPrice(total())}</span>
        </div>
      </div>
    </div>
  );
}
