"use client";

import { CheckCircle2, FileText } from "lucide-react";
import { PDFProduct } from "@/types";
import CurrencyPrice from "@/components/ui/CurrencyPrice";
import { useAuthenticatedResource } from "@/hooks/useAuthenticatedResource";
import { AddPdfToCartButton } from "@/components/course/AddToCartButtons";
import PdfViewer from "@/components/ui/PdfViewer";

export default function PdfAccessCard({ initialPdf }: { initialPdf: PDFProduct }) {
  const pdf = useAuthenticatedResource<PDFProduct>(`/catalog/pdfs/${initialPdf.slug}/`, initialPdf);
  const unlocked = pdf.is_free || pdf.is_purchased;

  return (
    <div className="card sticky top-24 overflow-hidden">
      <div className="flex aspect-[4/3] w-full items-center justify-center bg-gradient-to-br from-amber-50 to-orange-50">
        {pdf.cover_image ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img loading="lazy" decoding="async" src={pdf.cover_image} alt={pdf.title} className="h-full w-full object-cover" />
        ) : (
          <FileText size={56} className="text-amber-300" />
        )}
      </div>
      <div className="p-5">
        <span className="text-3xl font-extrabold"><CurrencyPrice value={pdf.price} /></span>
        <div className="mt-4">
          {unlocked ? (
            pdf.file ? <PdfViewer url={pdf.file} title={pdf.title} /> : <p className="text-sm text-gray-500">Fichier indisponible.</p>
          ) : (
            <AddPdfToCartButton pdf={pdf} />
          )}
        </div>
        {!unlocked && pdf.preview_file && (
          <div className="mt-2"><PdfViewer url={pdf.preview_file} title={`${pdf.title} · extrait gratuit`} /></div>
        )}
        <div className="mt-5 flex flex-col gap-2 border-t border-gray-100 pt-4 text-sm text-gray-600">
          <span className="flex items-center gap-2"><CheckCircle2 size={16} /> Téléchargement illimité après achat</span>
          <span className="flex items-center gap-2"><CheckCircle2 size={16} /> Mises à jour incluses</span>
          <span className="flex items-center gap-2"><CheckCircle2 size={16} /> Paiement sécurisé</span>
        </div>
      </div>
    </div>
  );
}
