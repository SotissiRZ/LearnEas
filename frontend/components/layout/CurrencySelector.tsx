"use client";

import { ChevronDown, Coins } from "lucide-react";
import { useCurrency } from "@/hooks/useCurrency";

export default function CurrencySelector({ mobile = false }: { mobile?: boolean }) {
  const currencies = useCurrency((state) => state.currencies);
  const selectedCode = useCurrency((state) => state.selectedCode);
  const loading = useCurrency((state) => state.loading);
  const selectCurrency = useCurrency((state) => state.selectCurrency);

  return (
    <label
      className={mobile
        ? "flex w-full items-center gap-3 rounded-xl border border-gray-200 bg-gray-50 px-3 py-2.5"
        : "relative hidden items-center sm:flex"}
      title="Devise d'affichage"
    >
      {mobile && <Coins size={17} className="shrink-0 text-brand-700" />}
      {mobile && <span className="mr-auto text-sm font-medium text-gray-700">Devise d'affichage</span>}
      <span className="sr-only">Devise d'affichage</span>
      <select
        aria-label="Devise d'affichage"
        value={selectedCode}
        disabled={loading}
        onChange={(event) => selectCurrency(event.target.value)}
        className={mobile
          ? "min-w-[96px] cursor-pointer appearance-none bg-transparent pr-5 text-right text-sm font-bold text-ink outline-none disabled:cursor-wait"
          : "h-10 min-w-[84px] cursor-pointer appearance-none rounded-full border border-gray-200 bg-white py-1 pl-3 pr-7 text-xs font-bold text-ink outline-none transition hover:border-brand-300 focus:border-brand-500 focus:ring-2 focus:ring-brand-100 disabled:cursor-wait disabled:opacity-60"}
      >
        {currencies.map((currency) => (
          <option key={currency.code} value={currency.code}>
            {currency.symbol ? `${currency.symbol} ` : ""}{currency.code}
          </option>
        ))}
      </select>
      <ChevronDown
        size={13}
        className={mobile ? "pointer-events-none -ml-5 text-gray-400" : "pointer-events-none absolute right-2 text-gray-400"}
      />
    </label>
  );
}
