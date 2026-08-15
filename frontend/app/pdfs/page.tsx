import { api } from "@/lib/api";
import { Category, PDFProduct, Paginated } from "@/types";
import PdfCard from "@/components/pdf/PdfCard";
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

export default async function PdfsPage({ searchParams }: Props) {
  const params = new URLSearchParams();
  if (searchParams.category) params.set("category__slug", searchParams.category);
  if (searchParams.level) params.set("level", searchParams.level);
  if (searchParams.is_free) params.set("is_free", searchParams.is_free);
  if (searchParams.search) params.set("search", searchParams.search);
  params.set("ordering", searchParams.ordering || "-created_at");
  if (searchParams.page) params.set("page", searchParams.page);

  const [data, categories] = await Promise.all([
    safeGet<Paginated<PDFProduct>>(`/catalog/pdfs/?${params.toString()}`, {
      count: 0, next: null, previous: null, results: [],
    }),
    safeGet<Category[]>("/catalog/categories/", []),
  ]);

  return (
    <div className="container-app py-10">
      <div className="mb-6">
        <h1 className="text-3xl font-extrabold">PDF & Guides</h1>
        <p className="mt-1 text-gray-500">
          {data.count} ressource{data.count > 1 ? "s" : ""} téléchargeable{data.count > 1 ? "s" : ""} — vendues indépendamment des cours vidéo.
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
            <div className="card p-10 text-center text-gray-500">Aucun PDF ne correspond à votre recherche.</div>
          ) : (
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-3">
              {data.results.map((p) => <PdfCard key={p.id} pdf={p} />)}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
