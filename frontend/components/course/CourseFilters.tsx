"use client";

import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { Category, Domain } from "@/types";

const LEVELS = [
  { value: "", label: "Tous niveaux" },
  { value: "beginner", label: "Débutant" },
  { value: "intermediate", label: "Intermédiaire" },
  { value: "expert", label: "Expert" },
];

const SORTS = [
  { value: "-created_at", label: "Plus récents" },
  { value: "price", label: "Prix croissant" },
  { value: "-price", label: "Prix décroissant" },
  { value: "-rating_avg", label: "Mieux notés" },
  { value: "-students_count", label: "Les plus suivis" },
];

export default function CourseFilters({
  domains,
  categories,
  current,
  showPrice = true,
  showSort = true,
  showCounts = true,
}: {
  domains: Domain[];
  categories: Category[];
  current: Record<string, string | undefined>;
  showPrice?: boolean;
  showSort?: boolean;
  showCounts?: boolean;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  function navigate(params: URLSearchParams) {
    params.delete("page");
    const query = params.toString();
    router.push(query ? `${pathname}?${query}` : pathname, { scroll: false });
  }

  function update(key: string, value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (value) params.set(key, value);
    else params.delete(key);
    navigate(params);
  }

  function updateDomain(value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (value) params.set("domain", value);
    else params.delete("domain");
    // Une catégorie appartient à un seul domaine : on évite de conserver une combinaison
    // incompatible lorsque l'utilisateur change de domaine.
    params.delete("category");
    navigate(params);
  }

  function clearAll() {
    const params = new URLSearchParams(searchParams.toString());
    ["domain", "category", "level", "is_free", "premium_included", "ordering", "page"].forEach((key) => params.delete(key));
    navigate(params);
  }

  const visibleCategories = current.domain
    ? categories.filter((category) => category.domain?.slug === current.domain)
    : categories;
  const hasFilters = Boolean(current.domain || current.category || current.level || current.is_free || current.premium_included || current.ordering);

  return (
    <div className="flex flex-col gap-6 text-sm">
      <div>
        <div className="mb-2 flex items-center justify-between gap-2">
          <p className="font-semibold text-gray-700">Domaine</p>
          {hasFilters && <button type="button" onClick={clearAll} className="text-[11px] font-bold text-brand-600 hover:text-brand-700">Réinitialiser</button>}
        </div>
        <div className="flex flex-col gap-1">
          <button
            onClick={() => updateDomain("")}
            className={`rounded-lg px-2 py-1.5 text-left ${!current.domain ? "bg-brand-50 font-semibold text-brand-700" : "hover:bg-gray-50"}`}
          >
            Tous les domaines
          </button>
          {domains.map((domain) => (
            <button
              key={domain.id}
              onClick={() => updateDomain(domain.slug)}
              className={`rounded-lg px-2 py-1.5 text-left ${current.domain === domain.slug ? "bg-brand-50 font-semibold text-brand-700" : "hover:bg-gray-50"}`}
            >
              {domain.name}{showCounts && typeof domain.courses_count === "number" && <span className="text-gray-400"> ({domain.courses_count})</span>}
            </button>
          ))}
        </div>
      </div>

      <div>
        <p className="mb-2 font-semibold text-gray-700">Catégorie</p>
        <div className="flex flex-col gap-1">
          <button
            onClick={() => update("category", "")}
            className={`rounded-lg px-2 py-1.5 text-left ${!current.category ? "bg-brand-50 font-semibold text-brand-700" : "hover:bg-gray-50"}`}
          >
            Toutes
          </button>
          {visibleCategories.map((category) => (
            <button
              key={category.id}
              onClick={() => update("category", category.slug)}
              className={`rounded-lg px-2 py-1.5 text-left ${current.category === category.slug ? "bg-brand-50 font-semibold text-brand-700" : "hover:bg-gray-50"}`}
            >
              {category.name}{showCounts && typeof category.courses_count === "number" && <span className="text-gray-400"> ({category.courses_count})</span>}
            </button>
          ))}
        </div>
      </div>

      <div>
        <p className="mb-2 font-semibold text-gray-700">Niveau</p>
        <select
          value={current.level || ""}
          onChange={(e) => update("level", e.target.value)}
          className="w-full rounded-lg border border-gray-200 px-2 py-2"
        >
          {LEVELS.map((level) => <option key={level.value} value={level.value}>{level.label}</option>)}
        </select>
      </div>

      {showPrice && (
        <div>
          <p className="mb-2 font-semibold text-gray-700">Prix</p>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={current.is_free === "true"}
              onChange={(e) => update("is_free", e.target.checked ? "true" : "")}
            />
            Gratuit uniquement
          </label>
        </div>
      )}

      <div>
        <p className="mb-2 font-semibold text-gray-700">KalanPro Premium</p>
        <label className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={current.premium_included === "true"}
            onChange={(e) => update("premium_included", e.target.checked ? "true" : "")}
          />
          Inclus dans Premium
        </label>
      </div>

      {showSort && (
        <div>
          <p className="mb-2 font-semibold text-gray-700">Trier par</p>
          <select
            value={current.ordering || "-created_at"}
            onChange={(e) => update("ordering", e.target.value)}
            className="w-full rounded-lg border border-gray-200 px-2 py-2"
          >
            {SORTS.map((sort) => <option key={sort.value} value={sort.value}>{sort.label}</option>)}
          </select>
        </div>
      )}
    </div>
  );
}
