"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { CreditCard, Loader2, ShieldCheck, Smartphone, WalletCards } from "lucide-react";
import { useCart } from "@/hooks/useCart";
import { useAuth } from "@/hooks/useAuth";
import { api, formatPrice, ApiError } from "@/lib/api";

type Currency = { id: number; code: string; name: string; symbol: string; exchange_rate: string; decimal_places: number; is_default: boolean };
type Gateway = { id: number; code: string; name: string; description: string; supported_currencies: string[]; configured: boolean; sandbox: boolean };
type PaymentConfig = { currencies: Currency[]; gateways: Gateway[]; default_currency: string };

function GatewayIcon({ code }: { code: string }) {
  if (code === "geniuspay") return <Smartphone size={20} />;
  if (code === "youcanpay") return <WalletCards size={20} />;
  return <CreditCard size={20} />;
}

export default function CheckoutPage() {
  const { items, total, clear } = useCart();
  const { user } = useAuth();
  const router = useRouter();
  const [config, setConfig] = useState<PaymentConfig | null>(null);
  const [provider, setProvider] = useState("");
  const [currency, setCurrency] = useState("MAD");
  const [loading, setLoading] = useState(false);
  const [configLoading, setConfigLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<PaymentConfig>("/payments/config/")
      .then((data) => {
        setConfig(data);
        setCurrency(data.default_currency || data.currencies[0]?.code || "MAD");
        const first = data.gateways.find((g) => g.configured && (!g.supported_currencies.length || g.supported_currencies.includes(data.default_currency))) || data.gateways[0];
        setProvider(first?.code || "");
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : "Impossible de charger les moyens de paiement."))
      .finally(() => setConfigLoading(false));
  }, []);

  const selectedCurrency = config?.currencies.find((item) => item.code === currency);
  const availableGateways = useMemo(() => (config?.gateways || []).filter((gateway) => !gateway.supported_currencies.length || gateway.supported_currencies.includes(currency)), [config, currency]);
  const convertedTotal = selectedCurrency ? total() * Number(selectedCurrency.exchange_rate || 1) : total();
  const isFreeCart = total() <= 0;

  useEffect(() => {
    if (!availableGateways.some((gateway) => gateway.code === provider)) {
      setProvider(availableGateways.find((g) => g.configured)?.code || availableGateways[0]?.code || "");
    }
  }, [availableGateways, provider]);

  async function handlePay() {
    if (!isFreeCart && !provider) { setError("Aucun moyen de paiement n'est disponible pour cette devise."); return; }
    setLoading(true);
    setError("");
    try {
      const course_ids = items.filter((i) => i.type === "course").map((i) => i.id);
      const pdf_ids = items.filter((i) => i.type === "pdf").map((i) => i.id);
      const formation_ids = items.filter((i) => i.type === "formation").map((i) => i.id);
      const res = await api.post<{ order: { id: number }; requires_payment: boolean; checkout_url?: string | null; manual_review?: boolean }>(
        "/payments/checkout/",
        { course_ids, pdf_ids, formation_ids, provider: provider || "manual", currency }
      );
      if (res.requires_payment && res.checkout_url) {
        window.location.assign(res.checkout_url);
        return;
      }
      if (res.manual_review) {
        clear();
        router.push(`/dashboard/student?payment_pending=1&order=${res.order.id}`);
        return;
      }
      clear();
      router.push("/dashboard/student?purchased=1");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Une erreur est survenue lors du paiement.");
    } finally {
      setLoading(false);
    }
  }

  if (!user) return <div className="container-app py-20 text-center text-gray-500">Veuillez vous connecter pour continuer.</div>;
  if (items.length === 0) return <div className="container-app py-20 text-center text-gray-500">Votre panier est vide.</div>;

  return (
    <div className="container-app grid grid-cols-1 gap-8 py-10 lg:grid-cols-[1fr_380px]">
      <div>
        <h1 className="mb-6 text-2xl font-extrabold">Paiement</h1>
        <div className="card p-5">
          <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
            <div><h2 className="font-semibold">Mode de paiement</h2><p className="text-xs text-gray-500">Les moyens disponibles sont configurés par l'administrateur.</p></div>
            <label className="text-xs font-medium text-gray-600">Devise
              <select value={currency} onChange={(e) => setCurrency(e.target.value)} className="input-admin ml-2 !py-2">
                {(config?.currencies || []).map((item) => <option key={item.code} value={item.code}>{item.code} · {item.name}</option>)}
              </select>
            </label>
          </div>

          {!isFreeCart && (configLoading ? <div className="py-8 text-center text-sm text-gray-400"><Loader2 className="mx-auto mb-2 animate-spin" />Chargement...</div> : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {availableGateways.map((gateway) => (
                <button key={gateway.code} type="button" disabled={!gateway.configured && gateway.code !== "manual"} onClick={() => setProvider(gateway.code)} className={`rounded-xl border p-4 text-left transition disabled:cursor-not-allowed disabled:opacity-45 ${provider === gateway.code ? "border-brand-600 bg-brand-50" : "border-gray-200 hover:border-brand-200"}`}>
                  <div className="mb-2 flex items-center justify-between"><span className="text-brand-700"><GatewayIcon code={gateway.code} /></span>{gateway.sandbox && <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-700">TEST</span>}</div>
                  <p className="font-semibold">{gateway.name}</p>
                  <p className="mt-1 text-xs text-gray-500">{gateway.description}</p>
                  {!gateway.configured && gateway.code !== "manual" && <p className="mt-2 text-[11px] font-semibold text-red-600">Clés serveur non configurées</p>}
                </button>
              ))}
              {availableGateways.length === 0 && <p className="col-span-full rounded-xl bg-amber-50 p-4 text-sm text-amber-800">Aucun moyen de paiement actif pour {currency}.</p>}
            </div>
          ))}

          {isFreeCart ? (
            <p className="rounded-xl bg-emerald-50 p-4 text-sm font-medium text-emerald-800">Ce panier est gratuit. Aucun moyen de paiement externe n’est requis.</p>
          ) : (
            <p className="mt-5 rounded-lg bg-gray-50 p-3 text-sm text-gray-600">LearnEas ne stocke jamais les numéros de carte. Les paiements externes sont finalisés sur la page sécurisée du prestataire activé.</p>
          )}
          {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
          <button onClick={handlePay} disabled={loading || (!isFreeCart && (configLoading || !provider))} className="btn-primary mt-5 w-full">
            {loading ? <Loader2 className="animate-spin" size={18} /> : <ShieldCheck size={18} />}
            {isFreeCart ? "Obtenir gratuitement" : <>Payer {selectedCurrency ? `${convertedTotal.toLocaleString("fr-FR", { maximumFractionDigits: selectedCurrency.decimal_places })} ${selectedCurrency.symbol || selectedCurrency.code}` : formatPrice(total())}</>}
          </button>
          <p className="mt-2 text-center text-xs text-gray-400">Paiement chiffré et sécurisé.</p>
        </div>
      </div>

      <div className="card h-fit p-5">
        <h2 className="mb-4 font-bold">Récapitulatif</h2>
        <div className="flex flex-col gap-2 text-sm">{items.map((item) => <div key={`${item.type}-${item.id}`} className="flex justify-between gap-3"><span className="line-clamp-1">{item.title}</span><span className="font-semibold">{formatPrice(item.price)}</span></div>)}</div>
        <div className="mt-4 flex items-center justify-between border-t border-gray-100 pt-4 text-lg font-extrabold"><span>Total de base</span><span>{formatPrice(total())}</span></div>
      </div>
    </div>
  );
}
