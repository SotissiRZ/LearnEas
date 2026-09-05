import Link from "next/link";
import { FileText, Download } from "lucide-react";
import { PDFProduct } from "@/types";
import CurrencyPrice from "@/components/ui/CurrencyPrice";
import RatingStars from "@/components/ui/RatingStars";
import LevelBadge from "@/components/ui/LevelBadge";
import QuickAddButton from "@/components/course/QuickAddButton";

export default function PdfCard({ pdf }: { pdf: PDFProduct }) {
  return (
    <Link
      href={`/pdfs/${pdf.slug}`}
      className="card catalog-card group flex flex-col overflow-hidden transition hover:-translate-y-1 hover:shadow-soft"
    >
      <div className="relative flex aspect-[4/3] w-full items-center justify-center overflow-hidden bg-gradient-to-br from-amber-50 to-orange-50">
        {pdf.cover_image ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img loading="lazy" decoding="async" src={pdf.cover_image} alt={pdf.title} className="h-full w-full object-cover object-center transition duration-300 group-hover:scale-[1.02]" />
        ) : (
          <FileText size={48} className="text-amber-300" />
        )}
        {pdf.is_free && <span className="badge absolute left-3 top-3 bg-white/95 text-brand-700 shadow">Gratuit</span>}
        <span className="badge absolute right-3 top-3 bg-white/95 text-amber-700 shadow">PDF</span>
      </div>

      <div className="flex flex-1 flex-col gap-1.5 p-3.5 sm:p-4">
        <div className="flex items-center gap-2">
          <LevelBadge level={pdf.level} />
          {pdf.category && <span className="text-xs font-medium text-gray-400">{pdf.category.name}</span>}
        </div>

        <h3 className="line-clamp-2 text-base font-bold leading-snug text-ink group-hover:text-brand-700">
          {pdf.title}
        </h3>
        <p className="text-xs font-medium text-gray-500">{pdf.instructor?.full_name}</p>

        <RatingStars value={parseFloat(pdf.rating_avg)} count={pdf.rating_count} />

        <div className="mt-1 flex items-center gap-3 text-xs text-gray-500">
          <span className="flex items-center gap-1"><FileText size={14} /> {pdf.page_count} pages</span>
          <span className="flex items-center gap-1"><Download size={14} /> {pdf.downloads_count}</span>
        </div>

        <div className="mt-auto flex items-center justify-between gap-2 pt-2">
          <span className="text-lg font-extrabold text-ink"><CurrencyPrice value={pdf.price} /></span>
          <QuickAddButton item={{ kind: "pdf", data: pdf }} />
        </div>
      </div>
    </Link>
  );
}
