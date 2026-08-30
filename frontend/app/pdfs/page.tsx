import { safeGet } from "@/lib/api";
import { Category, PDFProduct, Paginated } from "@/types";
import PdfCard from "@/components/pdf/PdfCard";
import CourseFilters from "@/components/course/CourseFilters";
import ApiErrorBanner from "@/components/ui/ApiErrorBanner";
import { SlidersHorizontal } from "lucide-react";

interface Props {
  searchParams: Promise<{
    category?: string;
    level?: string;
    is_free?: string;
    search?: string;
    ordering?: string;
    page?: string;
  }>;
}

export default async function PdfsPage({ searchParams }: Props) {
  const query = await searchParams;
  const params = new URLSearchParams();
  if (query.category) params.set("category__slug", query.category);
  if (query.level) params.set("level", query.level);
  if (query.is_free) params.set("is_free", query.is_free);
  if (query.search) params.set("search", query.search);
  params.set("ordering", query.ordering || "-created_at");
  if (query.page) params.set("page", query.page);

  const [pdfsResult, categoriesResult] = await Promise.all([
    safeGet<Paginated<PDFProduct>>(`/catalog/pdfs/?${params.toString()}`, {
      count: 0, next: null, previous: null, results: [],
    }),
    safeGet<Category[]>("/catalog/categories/", []),
  ]);
  const data = pdfsResult.data;
  const categories = categoriesResult.data;
  const hasError = !pdfsResult.ok || !categoriesResult.ok;

  return (
    <div className="container-app py-10">
      {hasError && <ApiErrorBanner message={pdfsResult.error || categoriesResult.error} />}

      <div className="mb-6">
        <h1 className="text-3xl font-extrabold">PDF & Guides</h1>
        <p className="mt-1 text-gray-500">
          {data.count} ressource{data.count > 1 ? "s" : ""} téléchargeable{data.count > 1 ? "s" : ""} · vendues indépendamment des cours vidéo.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[260px_1fr]">
        <aside className="hidden lg:block">
          <div className="card sticky top-24 p-5">
            <div className="mb-4 flex items-center gap-2 text-sm font-semibold">
              <SlidersHorizontal size={16} /> Filtres
            </div>
            <CourseFilters categories={categories} current={query} />
          </div>
        </aside>

        <div>
          {data.results.length === 0 ? (
            <div className="card p-10 text-center text-gray-500">
              {hasError ? "Le catalogue n'a pas pu être chargé." : "Aucun PDF ne correspond à votre recherche."}
            </div>
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
