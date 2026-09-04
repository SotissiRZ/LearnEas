"use client";

import { useMemo, useState } from "react";
import { Check, Search, X } from "lucide-react";
import { COUNTRY_OPTIONS, PRIORITY_COUNTRY_CODES, countryFlag } from "@/lib/countries";

const PRIORITY_SET = new Set(PRIORITY_COUNTRY_CODES);
const ORDERED_COUNTRIES = [
  ...PRIORITY_COUNTRY_CODES.map((code) => COUNTRY_OPTIONS.find((item) => item.code === code)).filter(Boolean),
  ...COUNTRY_OPTIONS.filter((item) => !PRIORITY_SET.has(item.code)),
] as typeof COUNTRY_OPTIONS;

export default function CountryMultiSelect({
  value,
  onChange,
  className = "",
}: {
  value: string[];
  onChange: (countries: string[]) => void;
  className?: string;
}) {
  const [query, setQuery] = useState("");
  const selected = new Set(value || []);

  const visible = useMemo(() => {
    const term = query.trim().toLocaleLowerCase("fr");
    if (!term) return ORDERED_COUNTRIES;
    return ORDERED_COUNTRIES.filter((country) =>
      `${country.label} ${country.name} ${country.code}`.toLocaleLowerCase("fr").includes(term)
    );
  }, [query]);

  function toggle(country: string) {
    const next = new Set(value || []);
    if (next.has(country)) next.delete(country);
    else next.add(country);
    onChange(Array.from(next));
  }

  return (
    <div className={`rounded-xl border border-gray-200 bg-white ${className}`}>
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1.5 border-b border-gray-100 p-3">
          {value.map((countryName) => {
            const country = COUNTRY_OPTIONS.find((item) => item.name === countryName);
            return (
              <button
                key={countryName}
                type="button"
                onClick={() => toggle(countryName)}
                className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-2.5 py-1 text-[11px] font-semibold text-brand-700"
                title={`Retirer ${countryName}`}
              >
                {country ? countryFlag(country.code) : ""} {countryName} <X size={11} />
              </button>
            );
          })}
        </div>
      )}
      <div className="relative border-b border-gray-100 p-2.5">
        <Search size={14} className="pointer-events-none absolute left-5 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          className="w-full rounded-lg border border-gray-200 py-2 pl-8 pr-3 text-sm outline-none focus:border-brand-300 focus:ring-2 focus:ring-brand-100"
          placeholder="Rechercher dans la liste des pays"
          aria-label="Filtrer la liste des pays"
        />
      </div>
      <div className="max-h-56 overflow-y-auto p-2" role="group" aria-label="Pays souhaités">
        {visible.map((country) => {
          const checked = selected.has(country.name);
          return (
            <button
              key={country.code}
              type="button"
              onClick={() => toggle(country.name)}
              className={`flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm transition ${checked ? "bg-brand-50 text-brand-800" : "hover:bg-gray-50"}`}
              aria-pressed={checked}
            >
              <span className={`grid h-5 w-5 shrink-0 place-items-center rounded border ${checked ? "border-brand-600 bg-brand-600 text-white" : "border-gray-300 bg-white"}`}>
                {checked && <Check size={13} />}
              </span>
              <span className="shrink-0">{countryFlag(country.code)}</span>
              <span className="min-w-0 flex-1 truncate">{country.label}</span>
            </button>
          );
        })}
        {visible.length === 0 && <p className="px-3 py-5 text-center text-xs text-gray-400">Aucun pays correspondant.</p>}
      </div>
    </div>
  );
}
