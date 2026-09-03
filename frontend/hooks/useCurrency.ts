"use client";

import { create } from "zustand";
import { api } from "@/lib/api";

export type DisplayCurrency = {
  id: number;
  code: string;
  name: string;
  symbol: string;
  exchange_rate: string;
  decimal_places: number;
  is_default: boolean;
};

type PaymentCurrencyConfig = {
  currencies: DisplayCurrency[];
  default_currency: string;
};

type CurrencyState = {
  currencies: DisplayCurrency[];
  selectedCode: string;
  defaultCode: string;
  loading: boolean;
  hydrated: boolean;
  error: string | null;
  hydrate: () => Promise<void>;
  selectCurrency: (code: string) => void;
};

const STORAGE_KEY = "learneas.display_currency";
const COOKIE_KEY = "learneas_currency";
const FALLBACK_EUR: DisplayCurrency = {
  id: 0,
  code: "EUR",
  name: "Euro",
  symbol: "€",
  exchange_rate: "1",
  decimal_places: 2,
  is_default: true,
};

function readStoredCurrency(): string | null {
  if (typeof window === "undefined") return null;
  const value = window.localStorage.getItem(STORAGE_KEY)?.trim().toUpperCase();
  return value && /^[A-Z]{3}$/.test(value) ? value : null;
}

function persistCurrency(code: string) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, code);
  document.cookie = `${COOKIE_KEY}=${encodeURIComponent(code)}; Path=/; Max-Age=31536000; SameSite=Lax`;
}

function normalizeCurrencies(items: DisplayCurrency[] | undefined): DisplayCurrency[] {
  const source = Array.isArray(items) && items.length ? items : [FALLBACK_EUR];
  const seen = new Set<string>();
  const normalized = source
    .filter((item) => item && typeof item.code === "string")
    .map((item) => ({
      ...item,
      code: item.code.trim().toUpperCase(),
      exchange_rate: String(item.exchange_rate || "1"),
      decimal_places: Math.min(2, Math.max(0, Number(item.decimal_places ?? 2))),
    }))
    .filter((item) => {
      if (!/^[A-Z]{3}$/.test(item.code) || seen.has(item.code)) return false;
      seen.add(item.code);
      return true;
    });

  if (!normalized.some((item) => item.code === "EUR")) normalized.unshift(FALLBACK_EUR);
  return normalized;
}

export const useCurrency = create<CurrencyState>((set, get) => ({
  currencies: [FALLBACK_EUR],
  selectedCode: "EUR",
  defaultCode: "EUR",
  loading: false,
  hydrated: false,
  error: null,

  hydrate: async () => {
    if (get().loading || get().hydrated) return;
    set({ loading: true, error: null });
    try {
      const data = await api.get<PaymentCurrencyConfig>("/payments/config/");
      const currencies = normalizeCurrencies(data.currencies);
      const defaultCode = currencies.some((item) => item.code === data.default_currency)
        ? data.default_currency
        : currencies.find((item) => item.is_default)?.code || "EUR";
      const stored = readStoredCurrency();
      const selectedCode = stored && currencies.some((item) => item.code === stored) ? stored : defaultCode;
      persistCurrency(selectedCode);
      set({ currencies, defaultCode, selectedCode, loading: false, hydrated: true, error: null });
    } catch {
      const selectedCode = "EUR";
      persistCurrency(selectedCode);
      set({
        currencies: [FALLBACK_EUR],
        selectedCode,
        defaultCode: "EUR",
        loading: false,
        hydrated: true,
        error: "Les devises n'ont pas pu être chargées.",
      });
    }
  },

  selectCurrency: (code) => {
    const normalized = code.trim().toUpperCase();
    if (!get().currencies.some((item) => item.code === normalized)) return;
    persistCurrency(normalized);
    set({ selectedCode: normalized });
  },
}));

export function convertFromEur(value: number | string, currency: DisplayCurrency): number {
  const amount = typeof value === "string" ? Number.parseFloat(value) : value;
  if (!Number.isFinite(amount)) return 0;
  const rate = Number.parseFloat(currency.exchange_rate || "1");
  return amount * (Number.isFinite(rate) && rate > 0 ? rate : 1);
}


export function formatCurrencyValue(value: number | string, currency: DisplayCurrency): string {
  const amount = typeof value === "string" ? Number.parseFloat(value) : value;
  if (!Number.isFinite(amount)) return "—";
  if (amount === 0) return "Gratuit";
  const digits = Math.min(2, Math.max(0, Number(currency.decimal_places ?? 2)));
  try {
    return new Intl.NumberFormat("fr-FR", {
      style: "currency",
      currency: currency.code,
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }).format(amount);
  } catch {
    return `${amount.toLocaleString("fr-FR", { minimumFractionDigits: digits, maximumFractionDigits: digits })} ${currency.symbol || currency.code}`;
  }
}

export function formatDisplayPrice(value: number | string, currency: DisplayCurrency): string {
  const amount = typeof value === "string" ? Number.parseFloat(value) : value;
  if (!Number.isFinite(amount)) return "—";
  if (amount === 0) return "Gratuit";
  const converted = convertFromEur(amount, currency);
  const digits = Math.min(2, Math.max(0, Number(currency.decimal_places ?? 2)));
  try {
    return new Intl.NumberFormat("fr-FR", {
      style: "currency",
      currency: currency.code,
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    }).format(converted);
  } catch {
    return `${converted.toLocaleString("fr-FR", { minimumFractionDigits: digits, maximumFractionDigits: digits })} ${currency.symbol || currency.code}`;
  }
}
