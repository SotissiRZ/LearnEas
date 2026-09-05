import { safePublicGet } from "@/lib/serverPublicApi";
import { Category, Domain, InteractiveFormation, Paginated } from "@/types";
import FormationCard from "@/components/formation/FormationCard";
import CourseFilters from "@/components/course/CourseFilters";
import ApiErrorBanner from "@/components/ui/ApiErrorBanner";
import { SlidersHorizontal, Video } from "lucide-react";

interface Props {
  searchParams: Promise<{
    domain?: string;
    category?: string;
    level?: string;
    search?: string;
    page?: string;
  }>;
}

export default async function FormationsPage({ searchParams }: Props) {
  const query = await searchParams;
  const params = new URLSearchParams();
  if (query.domain) params.set("category__domain__slug", query.domain);
  if (query.category) params.set("category__slug", query.category);
  if (query.level) params.set("level", query.level);
  if (query.search) params.set("search", query.search);
  if (query.page) params.set("page", query.page);
  params.set("ordering", "start_date");

  const [formationsResult, categoriesResult, domainsResult] = await Promise.all([
    safePublicGet<Paginated<InteractiveFormation> | InteractiveFormation[]>(`/formations/?${params.toString()}`, [], 30),
    safePublicGet<Category[]>("/catalog/categories/", [], 300),
    safePublicGet<Domain[]>("/catalog/domains/", [], 300),
  ]);
  const formations = Array.isArray(formationsResult.data) ? formationsResult.data : formationsResult.data.results;
  const categories = categoriesResult.data;
  const domains = domainsResult.data;
  const hasError = !formationsResult.ok || !categoriesResult.ok || !domainsResult.ok;

  return (
    <div className="container-app py-10">
      {hasError && <ApiErrorBanner message={formationsResult.error || categoriesResult.error || domainsResult.error} />}

      <div className="mb-6 flex items-center gap-3">
        <div className="grid h-11 w-11 place-items-center rounded-xl bg-brand-50 text-brand-600">
          <Video size={22} />
        </div>
        <div>
          <h1 className="text-3xl font-extrabold">Cohortes live</h1>
          <p className="mt-1 text-gray-500">
            Programmes accompagnés en petit groupe, filtrables par domaine, catégorie et niveau.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[260px_1fr]">
        <details className="card p-4 lg:hidden">
          <summary className="flex cursor-pointer list-none items-center gap-2 text-sm font-bold text-navy-950">
            <SlidersHorizontal size={16} /> Filtres et domaines
          </summary>
          <div className="mt-5 border-t border-slate-100 pt-5">
            <CourseFilters domains={domains} categories={categories} current={query} showPrice={false} showSort={false} showCounts={false} />
          </div>
        </details>

        <aside className="hidden lg:block">
          <div className="card sticky top-24 p-5">
            <div className="mb-4 flex items-center gap-2 text-sm font-semibold">
              <SlidersHorizontal size={16} /> Filtres
            </div>
            <CourseFilters domains={domains} categories={categories} current={query} showPrice={false} showSort={false} showCounts={false} />
          </div>
        </aside>

        <div>
          {formations.length === 0 ? (
            <div className="card p-10 text-center text-gray-500">
              {formationsResult.ok
                ? "Aucune cohorte ne correspond à ces filtres pour le moment."
                : "Le catalogue n'a pas pu être chargé."}
            </div>
          ) : (
            <div className="catalog-grid">
              {formations.map((formation) => <FormationCard key={formation.id} formation={formation} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
