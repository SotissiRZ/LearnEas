import { notFound } from "next/navigation";
import { FileText, Download, Globe, BarChart3, Lock, CheckCircle2 } from "lucide-react";
import { api, formatPrice } from "@/lib/api";
import { PDFProduct } from "@/types";
import RatingStars from "@/components/ui/RatingStars";
import LevelBadge from "@/components/ui/LevelBadge";
import { AddPdfToCartButton } from "@/components/course/AddToCartButtons";
import ContactInstructorButton from "@/components/chat/ContactInstructorButton";
import PdfViewer from "@/components/ui/PdfViewer";

async function getPdf(slug: string): Promise<PDFProduct | null> {
  try {
    return await api.get<PDFProduct>(`/catalog/pdfs/${slug}/`);
  } catch {
    return null;
  }
}

export default async function PdfDetailPage({ params }: { params: { slug: string } }) {
  const pdf = await getPdf(params.slug);
  if (!pdf) notFound();

  const unlocked = pdf.is_free || pdf.is_purchased;

  return (
    <div className="container-app grid grid-cols-1 gap-10 py-10 lg:grid-cols-[1fr_380px]">
      <div className="flex flex-col gap-8">
        <div>
          {pdf.category && <span className="text-sm font-semibold text-brand-700">{pdf.category.name}</span>}
          <h1 className="mt-1 text-3xl font-extrabold">{pdf.title}</h1>
          <div className="mt-3 flex flex-wrap items-center gap-4 text-sm">
            <RatingStars value={parseFloat(pdf.rating_avg)} count={pdf.rating_count} />
            <LevelBadge level={pdf.level} />
            <span className="flex items-center gap-1 text-gray-500"><Globe size={16} /> {pdf.language}</span>
            <span className="flex items-center gap-1 text-gray-500"><FileText size={16} /> {pdf.page_count} pages</span>
          </div>
          <p className="mt-2 text-sm text-gray-500">Par <span className="font-semibold">{pdf.instructor.full_name}</span></p>
        </div>

        <div className="card p-6">
          <h2 className="mb-3 text-xl font-bold">Description</h2>
          <p className="whitespace-pre-line text-sm leading-relaxed text-gray-600">{pdf.description}</p>
        </div>

        <div className="card p-6">
          <h2 className="mb-4 flex items-center gap-2 text-xl font-bold"><BarChart3 size={20} /> Auteur</h2>
          <div className="flex items-start gap-4">
            <div className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-brand-100 text-lg font-bold text-brand-700">
              {pdf.instructor.full_name[0]}
            </div>
            <div>
              <p className="font-bold">{pdf.instructor.full_name}</p>
              <p className="text-sm text-gray-500">{pdf.instructor.headline}</p>
              <ContactInstructorButton instructor={pdf.instructor} />
            </div>
          </div>
        </div>
      </div>

      <div>
        <div className="card sticky top-24 overflow-hidden">
          <div className="flex aspect-[4/3] w-full items-center justify-center bg-gradient-to-br from-amber-50 to-orange-50">
            {pdf.cover_image ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={pdf.cover_image} alt={pdf.title} className="h-full w-full object-cover" />
            ) : (
              <FileText size={56} className="text-amber-300" />
            )}
          </div>
          <div className="p-5">
            <span className="text-3xl font-extrabold">{formatPrice(pdf.price)}</span>

            <div className="mt-4">
              {unlocked ? (
                pdf.file ? (
                  <PdfViewer url={pdf.file} title={pdf.title} />
                ) : (
                  <p className="text-sm text-gray-500">Fichier indisponible.</p>
                )
              ) : (
                <AddPdfToCartButton pdf={pdf} />
              )}
            </div>

            {!unlocked && pdf.preview_file && (
              <div className="mt-2">
                <PdfViewer url={pdf.preview_file} title={`${pdf.title} — extrait gratuit`} />
              </div>
            )}

            <div className="mt-5 flex flex-col gap-2 border-t border-gray-100 pt-4 text-sm text-gray-600">
              <span className="flex items-center gap-2"><CheckCircle2 size={16} /> Téléchargement illimité après achat</span>
              <span className="flex items-center gap-2"><CheckCircle2 size={16} /> Mises à jour incluses</span>
              <span className="flex items-center gap-2"><CheckCircle2 size={16} /> Paiement sécurisé</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
