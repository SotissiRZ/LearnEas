"use client";

import type { SelectHTMLAttributes } from "react";
import {
  COUNTRY_OPTIONS,
  PRIORITY_COUNTRY_CODES,
  countryFlag,
  findCountryByName,
} from "@/lib/countries";

type Props = Omit<SelectHTMLAttributes<HTMLSelectElement>, "value" | "onChange"> & {
  value?: string | null;
  onChange: (countryName: string) => void;
  emptyLabel?: string;
};

const priority = new Set<string>(PRIORITY_COUNTRY_CODES);
const priorityCountries = PRIORITY_COUNTRY_CODES
  .map((code) => COUNTRY_OPTIONS.find((item) => item.code === code))
  .filter((item): item is (typeof COUNTRY_OPTIONS)[number] => Boolean(item));
const otherCountries = COUNTRY_OPTIONS.filter((item) => !priority.has(item.code));

export default function CountrySelect({
  value,
  onChange,
  emptyLabel = "Sélectionnez un pays",
  className = "input-admin w-full",
  required,
  ...props
}: Props) {
  const canonical = findCountryByName(value);
  const selectedValue = canonical?.name || "";

  return (
    <select
      {...props}
      required={required}
      value={selectedValue}
      onChange={(event) => onChange(event.target.value)}
      className={className}
    >
      <option value="">{emptyLabel}</option>
      <optgroup label="Afrique francophone et marchés prioritaires">
        {priorityCountries.map((country) => (
          <option key={`priority-${country.code}`} value={country.name}>
            {countryFlag(country.code)} {country.label}
          </option>
        ))}
      </optgroup>
      <optgroup label="Tous les pays et territoires">
        {otherCountries.map((country) => (
          <option key={country.code} value={country.name}>
            {countryFlag(country.code)} {country.label}
          </option>
        ))}
      </optgroup>
    </select>
  );
}
