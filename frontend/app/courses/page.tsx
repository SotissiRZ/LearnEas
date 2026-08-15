import { api } from "@/lib/api";
import { Category, Course, Paginated } from "@/types";
import CourseCard from "@/components/course/CourseCard";
import CourseFilters from "@/components/course/CourseFilters";
import { SlidersHorizontal } from "lucide-react";

async function safeGet<T>(path: string, fallback: T): Promise<T> {
  try {
    return await api.get<T>(path);
  } catch {
    return fallback;
  }
}

interface Props {
  searchParams: {
    category?: string;
    level?: string;
    is_free?: string;
    search?: string;
    ordering?: string;
    page?: string;
  };
}

export default async function CoursesPage({ searchParams }: Props) {
  const params = new URLSearchParams();
  if (searchParams.category) params.set("category__slug", searchParams.category);
  if (searchParams.level) params.set("level", searchParams.level);
  if (searchParams.is_free) params.set("is_free", searchParams.is_free);
  if (searchParams.search) params.set("search", searchParams.search);
  params.set("ordering", searchParams.ordering || "-created_at");
  if (searchParams.page) params.set("page", searchParams.page);

  const [data, categories] = await Promise.all([
    safeGet<Paginated<Course>>(`/catalog/courses/?${params.toString()}`, {
      count: 0, next: null, previous: null, results: [],
    }),
    safeGet<Category[]>("/catalog/categories/", []),
  ]);

  return (
    <div className="container-app py-10">
      <div className="mb-6">
        <h1 className="text-3xl font-extrabold">Tous les cours</h1>
        <p className="mt-1 text-gray-500">
          {data.count} cours complet{data.count > 1 ? "s" : ""} — accès à la playlist entière dès l'achat.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[260px_1fr]">
        <aside className="hidden lg:block">
          <div className="card sticky top-24 p-5">
            <div className="mb-4 flex items-center gap-2 text-sm font-semibold">
              <SlidersHorizontal size={16} /> Filtres
            </div>
            <CourseFilters categories={categories} current={searchParams} />
          </div>
        </aside>

        <div>
          {data.results.length === 0 ? (
            <div className="card p-10 text-center text-gray-500">
              Aucun cours ne correspond à votre recherche pour le moment.
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-3">
              {data.results.map((c) => <CourseCard key={c.id} course={c} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
