"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { FileText } from "lucide-react";
import { api } from "@/lib/api";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import DashboardNav from "@/components/dashboard/DashboardNav";
import GuardScreen from "@/components/ui/GuardScreen";
import PdfViewer from "@/components/ui/PdfViewer";

interface PDFPurchase {
  id: number;
  pdf_product: { id: number; title: string; slug: string; file?: string | null; cover_image: string | null; page_count: number };
  purchased_at: string;
}

export default function StudentPdfsPage() {
  const { ready } = useAuthGuard();
  const [purchases, setPurchases] = useState<PDFPurchase[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ready) return;
    api.get<{ results: PDFPurchase[] } | PDFPurchase[]>("/enrollments/my-pdfs/")
      .then((data: any) => setPurchases(data.results || data))
      .finally(() => setLoading(false));
  }, [ready]);

  if (!ready) return <GuardScreen />;

  return (
    <div className="container-app py-10">
      <DashboardNav role="student" />
      <h2 className="mb-4 text-xl font-bold">Mes PDF achetés</h2>
      {loading ? (
        <p className="text-gray-500">Chargement...</p>
      ) : purchases.length === 0 ? (
        <div className="card p-10 text-center text-gray-500">
          Aucun PDF acheté. <Link href="/pdfs" className="font-semibold text-brand-700">Explorer le catalogue</Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {purchases.map((p) => (
            <div key={p.id} className="card flex items-center gap-4 p-4">
              <div className="grid h-14 w-14 shrink-0 place-items-center rounded-lg bg-amber-50 text-amber-600">
                <FileText size={22} />
              </div>
              <div className="flex-1">
                <p className="line-clamp-2 font-semibold">{p.pdf_product.title}</p>
                <p className="text-xs text-gray-400">{p.pdf_product.page_count} pages</p>
              </div>
              {p.pdf_product.file && <PdfViewer url={p.pdf_product.file} title={p.pdf_product.title} />}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
