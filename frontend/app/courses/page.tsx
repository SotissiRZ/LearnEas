import { safePublicGet } from "@/lib/serverPublicApi";
import { Category, Course, Domain, Paginated } from "@/types";
import CourseCard from "@/components/course/CourseCard";
import CourseFilters from "@/components/course/CourseFilters";
import ApiErrorBanner from "@/components/ui/ApiErrorBanner";
import { SlidersHorizontal } from "lucide-react";

interface Props {
  searchParams: Promise<{
    category?: string;
    domain?: string;
    level?: string;
    is_free?: string;
    search?: string;
    ordering?: string;
    page?: string;
  }>;
}

export default async function CoursesPage({ searchParams }: Props) {
  const query = await searchParams;
  const params = new URLSearchParams();
  if (query.domain) params.set("category__domain__slug", query.domain);
  if (query.category) params.set("category__slug", query.category);
  if (query.level) params.set("level", query.level);
  if (query.is_free) params.set("is_free", query.is_free);
  if (query.search) params.set("search", query.search);
  params.set("ordering", query.ordering || "-created_at");
  if (query.page) params.set("page", query.page);

  const [coursesResult, categoriesResult, domainsResult] = await Promise.all([
    safePublicGet<Paginated<Course>>(`/catalog/courses/?${params.toString()}`, {
      count: 0, next: null, previous: null, results: [],
    }, 30),
    safePublicGet<Category[]>("/catalog/categories/", [], 300),
    safePublicGet<Domain[]>("/catalog/domains/", [], 300),
  ]);
  const data = coursesResult.data;
  const categories = categoriesResult.data;
  const domains = domainsResult.data;
  const hasError = !coursesResult.ok || !categoriesResult.ok || !domainsResult.ok;

  return (
    <div className="container-app py-10">
      {hasError && <ApiErrorBanner message={coursesResult.error || categoriesResult.error || domainsResult.error} />}

      <div className="mb-6">
        <h1 className="text-3xl font-extrabold">Tous les cours</h1>
        <p className="mt-1 text-gray-500">
          {data.count} cours complet{data.count > 1 ? "s" : ""} · accès à la playlist entière dès l'achat.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[260px_1fr]">
        <details className="card p-4 lg:hidden">
          <summary className="flex cursor-pointer list-none items-center gap-2 text-sm font-bold text-navy-950">
            <SlidersHorizontal size={16} /> Filtres et domaines
          </summary>
          <div className="mt-5 border-t border-slate-100 pt-5">
            <CourseFilters domains={domains} categories={categories} current={query} />
          </div>
        </details>
        <aside className="hidden lg:block">
          <div className="card sticky top-24 p-5">
            <div className="mb-4 flex items-center gap-2 text-sm font-semibold">
              <SlidersHorizontal size={16} /> Filtres
            </div>
            <CourseFilters domains={domains} categories={categories} current={query} />
          </div>
        </aside>

        <div>
          {data.results.length === 0 ? (
            <div className="card p-10 text-center text-gray-500">
              {hasError
                ? "Le catalogue n'a pas pu être chargé."
                : "Aucun cours ne correspond à votre recherche pour le moment."}
            </div>
          ) : (
            <div className="catalog-grid">
              {data.results.map((c) => <CourseCard key={c.id} course={c} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
