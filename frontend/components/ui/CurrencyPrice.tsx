"use client";

import { formatCurrencyValue, formatDisplayPrice, useCurrency } from "@/hooks/useCurrency";

export default function CurrencyPrice({ value }: { value: number | string }) {
  const currencies = useCurrency((state) => state.currencies);
  const selectedCode = useCurrency((state) => state.selectedCode);
  const currency = currencies.find((item) => item.code === selectedCode) || currencies[0];
  return <>{formatDisplayPrice(value, currency)}</>;
}

/** Affiche un montant qui est déjà libellé dans sa devise (ex. total historique d'une commande). */
export function CurrencyValue({ value, code }: { value: number | string; code: string }) {
  const currencies = useCurrency((state) => state.currencies);
  const normalized = (code || "EUR").toUpperCase();
  const currency = currencies.find((item) => item.code === normalized) || {
    id: 0, code: normalized, name: normalized, symbol: normalized, exchange_rate: "1", decimal_places: 2, is_default: false,
  };
  return <>{formatCurrencyValue(value, currency)}</>;
}
