"use client";

import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { Category } from "@/types";

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
  categories,
  current,
}: {
  categories: Category[];
  current: Record<string, string | undefined>;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  function update(key: string, value: string) {
    const params = new URLSearchParams(searchParams.toString());
    if (value) params.set(key, value);
    else params.delete(key);
    router.push(`${pathname}?${params.toString()}`);
  }

  return (
    <div className="flex flex-col gap-6 text-sm">
      <div>
        <p className="mb-2 font-semibold text-gray-700">Catégorie</p>
        <div className="flex flex-col gap-1">
          <button
            onClick={() => update("category", "")}
            className={`rounded-lg px-2 py-1.5 text-left ${!current.category ? "bg-brand-50 font-semibold text-brand-700" : "hover:bg-gray-50"}`}
          >
            Toutes
          </button>
          {categories.map((c) => (
            <button
              key={c.id}
              onClick={() => update("category", c.slug)}
              className={`rounded-lg px-2 py-1.5 text-left ${current.category === c.slug ? "bg-brand-50 font-semibold text-brand-700" : "hover:bg-gray-50"}`}
            >
              {c.name} <span className="text-gray-400">({c.courses_count})</span>
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
          {LEVELS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
        </select>
      </div>

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

      <div>
        <p className="mb-2 font-semibold text-gray-700">Trier par</p>
        <select
          value={current.ordering || "-created_at"}
          onChange={(e) => update("ordering", e.target.value)}
          className="w-full rounded-lg border border-gray-200 px-2 py-2"
        >
          {SORTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
        </select>
      </div>
    </div>
  );
}
