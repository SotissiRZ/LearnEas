"use client";

import { useEffect, useMemo, useState } from "react";
import {
  COUNTRY_OPTIONS,
  PRIORITY_COUNTRY_CODES,
  buildE164,
  countryFlag,
  findCountryByName,
  getCountryByCode,
  inferCountryFromPhone,
  phoneDigits,
} from "@/lib/countries";

type Props = {
  value: string;
  onChange: (e164: string) => void;
  preferredCountry?: string | null;
  label?: string;
  helperText?: string;
  required?: boolean;
  disabled?: boolean;
  className?: string;
};

const phoneCountries = COUNTRY_OPTIONS.filter((country) => Boolean(country.dialCode));
const priority = new Set<string>(PRIORITY_COUNTRY_CODES);
const priorityPhoneCountries = PRIORITY_COUNTRY_CODES
  .map((code) => phoneCountries.find((item) => item.code === code))
  .filter((item): item is (typeof phoneCountries)[number] => Boolean(item));
const otherPhoneCountries = phoneCountries.filter((country) => !priority.has(country.code));

function initialCountryCode(value: string, preferredCountry?: string | null): string {
  const preferred = findCountryByName(preferredCountry);
  const normalizedDigits = phoneDigits(value);
  const preferredDial = preferred?.dialCode.replace(/\D/g, "") || "";
  if (preferred && preferredDial && normalizedDigits.startsWith(preferredDial)) return preferred.code;
  return inferCountryFromPhone(value)?.code || preferred?.code || "SN";
}

function maxNationalDigits(code: string): number {
  const dialLength = getCountryByCode(code)?.dialCode.replace(/\D/g, "").length || 0;
  return Math.max(1, 15 - dialLength);
}

function sanitizeNationalNumber(value: string, code: string): string {
  return phoneDigits(value).slice(0, maxNationalDigits(code));
}

function extractNationalNumber(value: string, code: string): string {
  const digits = phoneDigits(value);
  const dial = getCountryByCode(code)?.dialCode.replace(/\D/g, "") || "";
  const national = dial && digits.startsWith(dial) ? digits.slice(dial.length) : digits;
  return sanitizeNationalNumber(national, code);
}

export default function InternationalPhoneField({
  value,
  onChange,
  preferredCountry,
  label = "Numéro de téléphone",
  helperText,
  required = false,
  disabled = false,
  className = "",
}: Props) {
  const [countryCode, setCountryCode] = useState(() => initialCountryCode(value, preferredCountry));
  const [nationalNumber, setNationalNumber] = useState(() => extractNationalNumber(value, initialCountryCode(value, preferredCountry)));

  useEffect(() => {
    if (value) {
      const nextCode = initialCountryCode(value, preferredCountry);
      setCountryCode(nextCode);
      setNationalNumber(extractNationalNumber(value, nextCode));
      return;
    }
    const preferred = findCountryByName(preferredCountry);
    if (preferred?.dialCode) setCountryCode(preferred.code);
  }, [value, preferredCountry]);

  const selectedCountry = useMemo(() => getCountryByCode(countryCode), [countryCode]);

  function changeCountry(nextCode: string) {
    const nextNational = sanitizeNationalNumber(nationalNumber, nextCode);
    setCountryCode(nextCode);
    setNationalNumber(nextNational);
    onChange(buildE164(nextCode, nextNational));
  }

  function changeNational(raw: string) {
    const next = sanitizeNationalNumber(raw, countryCode);
    setNationalNumber(next);
    onChange(buildE164(countryCode, next));
  }

  return (
    <label className={`block ${className}`.trim()}>
      <span className="mb-1 block text-xs font-medium text-gray-500">{label}</span>
      <div className="grid gap-2 sm:grid-cols-[minmax(170px,0.9fr)_minmax(0,1.1fr)]">
        <select
          aria-label="Indicatif téléphonique"
          value={countryCode}
          onChange={(event) => changeCountry(event.target.value)}
          disabled={disabled}
          className="input-admin min-w-0 w-full"
        >
          <optgroup label="Afrique francophone et marchés prioritaires">
            {priorityPhoneCountries.map((country) => (
              <option key={`phone-priority-${country.code}`} value={country.code}>
                {countryFlag(country.code)} {country.label} ({country.dialCode})
              </option>
            ))}
          </optgroup>
          <optgroup label="Tous les indicatifs">
            {otherPhoneCountries.map((country) => (
              <option key={`phone-${country.code}`} value={country.code}>
                {countryFlag(country.code)} {country.label} ({country.dialCode})
              </option>
            ))}
          </optgroup>
        </select>
        <div className="flex min-w-0 items-center rounded-lg border border-gray-200 bg-white focus-within:border-brand-500 focus-within:ring-2 focus-within:ring-brand-100">
          <span className="shrink-0 border-r border-gray-100 px-2.5 text-sm font-semibold text-gray-600">
            {selectedCountry?.dialCode || "+"}
          </span>
          <input
            type="tel"
            inputMode="numeric"
            autoComplete="tel-national"
            maxLength={maxNationalDigits(countryCode)}
            required={required}
            disabled={disabled}
            value={nationalNumber}
            onChange={(event) => changeNational(event.target.value)}
            placeholder="Numéro sans indicatif"
            className="min-w-0 flex-1 rounded-r-lg border-0 bg-transparent px-3 py-2 text-sm outline-none"
          />
        </div>
      </div>
      <span className="mt-1 block text-[11px] leading-4 text-gray-400">
        {helperText || `Indicatif sélectionné : ${selectedCountry?.dialCode || "—"}. Saisissez uniquement la partie nationale du numéro.`}
      </span>
    </label>
  );
}
