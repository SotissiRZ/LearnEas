"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { CreditCard, FlaskConical, Loader2, ShieldCheck, Smartphone, WalletCards } from "lucide-react";
import { useCart } from "@/hooks/useCart";
import { useAuth } from "@/hooks/useAuth";
import { api, apiFetch, ApiError } from "@/lib/api";
import CurrencyPrice from "@/components/ui/CurrencyPrice";
import { convertFromEur, formatCurrencyValue, formatDisplayPrice, useCurrency } from "@/hooks/useCurrency";

type Currency = { id: number; code: string; name: string; symbol: string; exchange_rate: string; decimal_places: number; is_default: boolean };
type Gateway = { id: number; code: string; name: string; description: string; supported_currencies: string[]; configured: boolean; sandbox: boolean };
type PaymentConfig = { currencies: Currency[]; gateways: Gateway[]; default_currency: string; test_payments_enabled?: boolean };
type EmployerProduct = "single_post" | "pro" | "business";
type LearnerProduct = "premium";
type EmployerPricing = {
  employer_single_post_eur: string;
  employer_pro_monthly_eur: string;
  employer_pro_active_jobs: number;
  employer_business_monthly_eur: string;
  employer_business_active_jobs: number;
  learner_premium_enabled: boolean;
  learner_premium_monthly_eur: string;
};

type CheckoutResponse = {
  order: { id: number; items?: Array<{ item_type?: string; entitlement_code?: string }> };
  requires_payment: boolean;
  checkout_url?: string | null;
  manual_review?: boolean;
  test_payment?: boolean;
  idempotent_replay?: boolean;
};

const employerTitles: Record<EmployerProduct, string> = {
  single_post: "Annonce recruteur à l’unité",
  pro: "KalanPro Pro recrutement",
  business: "KalanPro Business",
};

function isEmployerProduct(value: string | null): value is EmployerProduct {
  return value === "single_post" || value === "pro" || value === "business";
}

function GatewayIcon({ code }: { code: string }) {
  if (code === "geniuspay" || code === "cinetpay") return <Smartphone size={20} />;
  if (code === "youcanpay") return <WalletCards size={20} />;
  return <CreditCard size={20} />;
}

function newIdempotencyKey(scope: "employer" | "learner", product: EmployerProduct | LearnerProduct): string {
  const random = typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  return `${scope}-${product}-${random}`;
}

export default function CheckoutPage() {
  const { items, total, clear } = useCart();
  const { user } = useAuth();
  const router = useRouter();
  const params = useSearchParams();
  const productParam = params.get("employer_product");
  const learnerParam = params.get("learner_product");
  const employerProduct = isEmployerProduct(productParam) ? productParam : null;
  const learnerProduct: LearnerProduct | null = learnerParam === "premium" ? "premium" : null;
  const isEmployerCheckout = Boolean(employerProduct);
  const isLearnerCheckout = Boolean(learnerProduct);
  const isDedicatedCheckout = isEmployerCheckout || isLearnerCheckout;
  const idempotencyKeyRef = useRef<string | null>(null);
  const selectedDisplayCode = useCurrency((state) => state.selectedCode);
  const selectDisplayCurrency = useCurrency((state) => state.selectCurrency);
  const [config, setConfig] = useState<PaymentConfig | null>(null);
  const [employerPricing, setEmployerPricing] = useState<EmployerPricing | null>(null);
  const [provider, setProvider] = useState("");
  const [currency, setCurrency] = useState("EUR");
  const [loading, setLoading] = useState(false);
  const [configLoading, setConfigLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const requests: Promise<unknown>[] = [
      api.get<PaymentConfig>("/payments/config/").then((data) => {
        setConfig(data);
        const storedDisplayCode = useCurrency.getState().selectedCode;
        const preferred = data.currencies.some((item) => item.code === storedDisplayCode)
          ? storedDisplayCode
          : (data.default_currency || data.currencies[0]?.code || "EUR");
        setCurrency(preferred);
        const first = data.gateways.find((g) => g.configured && (!g.supported_currencies.length || g.supported_currencies.includes(preferred))) || data.gateways[0];
        setProvider(first?.code || (data.test_payments_enabled ? "__test__" : ""));
      }),
    ];
    if (isDedicatedCheckout) {
      requests.push(api.get<EmployerPricing>("/auth/platform-settings/").then(setEmployerPricing));
    }
    Promise.all(requests)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Impossible de charger les moyens de paiement."))
      .finally(() => setConfigLoading(false));
  }, [isDedicatedCheckout]);

  useEffect(() => {
    if (config?.currencies.some((item) => item.code === selectedDisplayCode) && selectedDisplayCode !== currency) {
      setCurrency(selectedDisplayCode);
    }
  }, [config, selectedDisplayCode, currency]);

  const employerAmount = useMemo(() => {
    if (!employerProduct || !employerPricing) return 0;
    const raw = employerProduct === "single_post"
      ? employerPricing.employer_single_post_eur
      : employerProduct === "pro"
        ? employerPricing.employer_pro_monthly_eur
        : employerPricing.employer_business_monthly_eur;
    const amount = Number(raw);
    return Number.isFinite(amount) ? amount : 0;
  }, [employerProduct, employerPricing]);

  const employerDetail = useMemo(() => {
    if (!employerProduct) return "";
    if (employerProduct === "single_post") return "1 annonce · jusqu’à 30 jours";
    const quota = employerProduct === "pro"
      ? employerPricing?.employer_pro_active_jobs
      : employerPricing?.employer_business_active_jobs;
    return `${quota ?? "—"} offres actives + vivier · 30 jours`;
  }, [employerProduct, employerPricing]);

  const learnerAmount = useMemo(() => {
    if (!learnerProduct || !employerPricing?.learner_premium_enabled) return 0;
    const amount = Number(employerPricing.learner_premium_monthly_eur);
    return Number.isFinite(amount) ? amount : 0;
  }, [learnerProduct, employerPricing]);

  const checkoutTotal = isEmployerCheckout ? employerAmount : isLearnerCheckout ? learnerAmount : total();
  const selectedCurrency = config?.currencies.find((item) => item.code === currency);
  const providerDisplayTotal = useMemo(() => {
    if (!selectedCurrency) return null;
    const converted = convertFromEur(checkoutTotal, selectedCurrency);
    if (provider === "cinetpay" && ["XOF", "XAF", "CDF", "GNF"].includes(selectedCurrency.code)) {
      const normalized = converted > 0 ? Math.max(5, Math.round(converted / 5) * 5) : 0;
      return formatCurrencyValue(normalized, selectedCurrency);
    }
    return formatCurrencyValue(converted, selectedCurrency);
  }, [provider, selectedCurrency, checkoutTotal]);

  const availableGateways = useMemo(
    () => (config?.gateways || []).filter((gateway) => !gateway.supported_currencies.length || gateway.supported_currencies.includes(currency)),
    [config, currency],
  );
  const isFreeCart = checkoutTotal <= 0;

  useEffect(() => {
    if (provider === "__test__" && config?.test_payments_enabled) return;
    if (!availableGateways.some((gateway) => gateway.code === provider)) {
      setProvider(availableGateways.find((g) => g.configured)?.code || availableGateways[0]?.code || (config?.test_payments_enabled ? "__test__" : ""));
    }
  }, [availableGateways, provider, config?.test_payments_enabled]);

  async function handlePay() {
    if (isEmployerCheckout && user?.role !== "employer") {
      setError("Ce checkout est réservé aux comptes entreprise/recruteur.");
      return;
    }
    if (isLearnerCheckout && user?.role !== "student") {
      setError("KalanPro Premium apprenant est réservé aux comptes étudiants.");
      return;
    }
    if (!isFreeCart && !provider) {
      setError("Aucun moyen de paiement n'est disponible pour cette devise.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const isTestPayment = provider === "__test__";
      let res: CheckoutResponse;
      if (employerProduct) {
        if (!idempotencyKeyRef.current) idempotencyKeyRef.current = newIdempotencyKey("employer", employerProduct);
        res = await apiFetch<CheckoutResponse>("/payments/checkout/", {
          method: "POST",
          headers: { "Idempotency-Key": idempotencyKeyRef.current },
          body: JSON.stringify({
            employer_product: employerProduct,
            provider: isTestPayment ? "manual" : (provider || "manual"),
            currency,
            test_payment: isTestPayment,
          }),
        });
      } else if (learnerProduct) {
        if (!idempotencyKeyRef.current) idempotencyKeyRef.current = newIdempotencyKey("learner", learnerProduct);
        res = await apiFetch<CheckoutResponse>("/payments/checkout/", {
          method: "POST",
          headers: { "Idempotency-Key": idempotencyKeyRef.current },
          body: JSON.stringify({
            learner_product: learnerProduct,
            provider: isTestPayment ? "manual" : (provider || "manual"),
            currency,
            test_payment: isTestPayment,
          }),
        });
      } else {
        const course_ids = items.filter((i) => i.type === "course").map((i) => i.id);
        const pdf_ids = items.filter((i) => i.type === "pdf").map((i) => i.id);
        const formation_ids = items.filter((i) => i.type === "formation").map((i) => i.id);
        const mentorship_booking_ids = items.filter((i) => i.type === "mentoring").map((i) => i.id);
        const mentorship_pack_ids = items.filter((i) => i.type === "mentor_pack").map((i) => i.id);
        res = await api.post<CheckoutResponse>(
          "/payments/checkout/",
          { course_ids, pdf_ids, formation_ids, mentorship_booking_ids, mentorship_pack_ids, provider: isTestPayment ? "manual" : (provider || "manual"), currency, test_payment: isTestPayment },
        );
      }

      if (res.requires_payment && res.checkout_url) {
        window.location.assign(res.checkout_url);
        return;
      }
      if (res.manual_review) {
        if (!isDedicatedCheckout) clear();
        router.push(isEmployerCheckout
          ? `/dashboard/employer?payment_pending=1&order=${res.order.id}`
          : `/dashboard/student?payment_pending=1&order=${res.order.id}`);
        return;
      }
      if (isEmployerCheckout) {
        router.push(`/dashboard/employer?billing=updated&order=${res.order.id}`);
        return;
      }
      if (isLearnerCheckout) {
        router.push(`/dashboard/student?premium=updated&order=${res.order.id}`);
        return;
      }
      const mentoringOnly = items.length > 0 && items.every((i) => i.type === "mentoring" || i.type === "mentor_pack");
      clear();
      router.push(mentoringOnly ? "/dashboard/student/mentorship?booked=1" : "/dashboard/student?purchased=1");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Une erreur est survenue lors du paiement.");
    } finally {
      setLoading(false);
    }
  }

  if (!user) return <div className="container-app py-20 text-center text-gray-500">Veuillez vous connecter pour continuer.</div>;
  if (isEmployerCheckout && user.role !== "employer") return <div className="container-app py-20 text-center text-gray-500">Cette offre est réservée aux comptes entreprise/recruteur.</div>;
  if (isLearnerCheckout && user.role !== "student") return <div className="container-app py-20 text-center text-gray-500">KalanPro Premium apprenant est réservé aux comptes étudiants.</div>;
  if (!isDedicatedCheckout && items.length === 0) return <div className="container-app py-20 text-center text-gray-500">Votre panier est vide.</div>;
  if (productParam && !employerProduct) return <div className="container-app py-20 text-center text-gray-500">Offre recruteur invalide.</div>;
  if (learnerParam && !learnerProduct) return <div className="container-app py-20 text-center text-gray-500">Offre Premium invalide.</div>;
  if (isLearnerCheckout && employerPricing && !employerPricing.learner_premium_enabled) return <div className="container-app py-20 text-center text-gray-500">KalanPro Premium est temporairement indisponible.</div>;

  return (
    <div className="container-app grid grid-cols-1 gap-8 py-10 lg:grid-cols-[1fr_380px]">
      <div>
        <h1 className="mb-6 text-2xl font-extrabold">Paiement</h1>
        <div className="card p-5">
          <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
            <div><h2 className="font-semibold">Mode de paiement</h2><p className="text-xs text-gray-500">Les moyens disponibles sont configurés par l'administrateur.</p></div>
            <label className="text-xs font-medium text-gray-600">Devise
              <select value={currency} onChange={(e) => { setCurrency(e.target.value); selectDisplayCurrency(e.target.value); }} className="input-admin ml-2 !py-2">
                {(config?.currencies || []).map((item) => <option key={item.code} value={item.code}>{item.code} · {item.name}</option>)}
              </select>
            </label>
          </div>

          {!isFreeCart && (configLoading ? <div className="py-8 text-center text-sm text-gray-400"><Loader2 className="mx-auto mb-2 animate-spin" />Chargement...</div> : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {config?.test_payments_enabled && (
                <button type="button" onClick={() => setProvider("__test__")} className={`relative overflow-hidden rounded-xl border p-4 text-left transition ${provider === "__test__" ? "border-violet-500 bg-violet-50 ring-2 ring-violet-100" : "border-violet-200 bg-white hover:border-violet-400"}`}>
                  <div className="mb-2 flex items-center justify-between"><span className="grid h-9 w-9 place-items-center rounded-lg bg-violet-100 text-violet-700"><FlaskConical size={19} /></span><span className="rounded-full bg-violet-100 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-violet-700">Sandbox local</span></div>
                  <p className="font-semibold text-violet-950">Paiement test KalanPro</p><p className="mt-1 text-xs leading-5 text-violet-700">Simule immédiatement un paiement réussi, sans carte et sans contacter de prestataire.</p>
                </button>
              )}
              {availableGateways.map((gateway) => (
                <button key={gateway.code} type="button" disabled={!gateway.configured && gateway.code !== "manual"} onClick={() => setProvider(gateway.code)} className={`rounded-xl border p-4 text-left transition disabled:cursor-not-allowed disabled:opacity-45 ${provider === gateway.code ? "border-brand-600 bg-brand-50" : "border-gray-200 hover:border-brand-200"}`}>
                  <div className="mb-2 flex items-center justify-between"><span className="text-brand-700"><GatewayIcon code={gateway.code} /></span>{gateway.sandbox && <span className="rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-semibold text-amber-700">TEST</span>}</div>
                  <p className="font-semibold">{gateway.name}</p><p className="mt-1 text-xs text-gray-500">{gateway.description}</p>{!gateway.configured && gateway.code !== "manual" && <p className="mt-2 text-[11px] font-semibold text-red-600">Clés serveur non configurées</p>}
                </button>
              ))}
              {availableGateways.length === 0 && !config?.test_payments_enabled && <p className="col-span-full rounded-xl bg-amber-50 p-4 text-sm text-amber-800">Aucun moyen de paiement actif pour {currency}.</p>}
            </div>
          ))}

          {isFreeCart ? <p className="rounded-xl bg-emerald-50 p-4 text-sm font-medium text-emerald-800">Ce panier est gratuit. Aucun moyen de paiement externe n’est requis.</p> : provider === "__test__" ? (
            <p className="mt-5 rounded-lg border border-violet-100 bg-violet-50 p-3 text-sm text-violet-800"><strong>Mode test :</strong> aucune transaction bancaire ne sera créée. L'accès sera accordé comme après un paiement réussi.</p>
          ) : (
            <p className="mt-5 rounded-lg bg-gray-50 p-3 text-sm text-gray-600">{provider === "cinetpay" ? "Vous serez redirigé vers CinetPay pour choisir le wallet Mobile Money disponible dans votre pays. Le montant CFA est arrondi au multiple de 5 requis par CinetPay." : "KalanPro ne stocke jamais les numéros de carte. Les paiements externes sont finalisés sur la page sécurisée du prestataire activé."}</p>
          )}
          {error && <p className="mt-3 text-sm text-red-600">{error}</p>}
          <button onClick={handlePay} disabled={loading || configLoading || (!isFreeCart && !provider) || (isDedicatedCheckout && !employerPricing)} className="btn-primary mt-5 w-full">
            {loading ? <Loader2 className="animate-spin" size={18} /> : <ShieldCheck size={18} />}
            {isFreeCart ? "Obtenir gratuitement" : provider === "__test__" ? <>Simuler le paiement · {selectedCurrency ? formatDisplayPrice(checkoutTotal, selectedCurrency) : <CurrencyPrice value={checkoutTotal} />}</> : <>Payer {providerDisplayTotal || (selectedCurrency ? formatDisplayPrice(checkoutTotal, selectedCurrency) : <CurrencyPrice value={checkoutTotal} />)}</>}
          </button>
          <p className="mt-2 text-center text-xs text-gray-400">Paiement chiffré et sécurisé. Les montants et droits d’accès sont recalculés côté serveur.</p>
        </div>
      </div>

      <div className="card h-fit p-5">
        <h2 className="mb-4 font-bold">Récapitulatif</h2>
        {employerProduct ? (
          <div className="text-sm"><div className="flex justify-between gap-3"><div><span className="font-semibold">{employerTitles[employerProduct]}</span><p className="mt-1 text-xs text-gray-500">{employerDetail}</p></div><span className="font-semibold"><CurrencyPrice value={employerAmount} /></span></div></div>
        ) : learnerProduct ? (
          <div className="text-sm"><div className="flex justify-between gap-3"><div><span className="font-semibold">KalanPro Premium apprenant</span><p className="mt-1 text-xs text-gray-500">Catalogue Premium cours + PDF · 30 jours · renouvellement chaîné</p></div><span className="font-semibold"><CurrencyPrice value={learnerAmount} /></span></div></div>
        ) : (
          <div className="flex flex-col gap-2 text-sm">{items.map((item) => <div key={`${item.type}-${item.id}`} className="flex justify-between gap-3"><span className="line-clamp-1">{item.title}</span><span className="font-semibold"><CurrencyPrice value={item.price} /></span></div>)}</div>
        )}
        <div className="mt-4 flex items-center justify-between border-t border-gray-100 pt-4 text-lg font-extrabold"><span>Total</span><span><CurrencyPrice value={checkoutTotal} /></span></div>
      </div>
    </div>
  );
}
