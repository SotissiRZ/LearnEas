"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PlusCircle, FileText, Download, Eye, EyeOff } from "lucide-react";
import { api, formatPrice } from "@/lib/api";
import { PDFProduct } from "@/types";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import DashboardNav from "@/components/dashboard/DashboardNav";
import GuardScreen from "@/components/ui/GuardScreen";
import PdfViewer from "@/components/ui/PdfViewer";

export default function InstructorPdfsPage() {
  const { ready } = useAuthGuard({ roles: ["instructor", "admin"], redirectTo: "/dashboard/instructor" });
  const [pdfs, setPdfs] = useState<PDFProduct[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ready) return;
    api.get<{ results: PDFProduct[] } | PDFProduct[]>("/catalog/pdfs/my_pdfs/")
      .then((d: any) => setPdfs(d.results || d))
      .finally(() => setLoading(false));
  }, [ready]);

  async function togglePublished(pdf: PDFProduct) {
    await api.patch(`/catalog/pdfs/${pdf.slug}/`, { published: !pdf.published });
    setPdfs((current) => current.map((item) => item.id === pdf.id ? { ...item, published: !item.published } : item));
  }

  if (!ready) return <GuardScreen />;

  return (
    <div className="container-app py-10">
      <DashboardNav role="instructor" />
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold">Mes PDF</h1>
        <Link href="/dashboard/instructor/pdfs/new" className="btn-primary !py-2 !text-sm">
          <PlusCircle size={16} /> Nouveau PDF
        </Link>
      </div>

      {loading ? (
        <p className="text-gray-500">Chargement...</p>
      ) : pdfs.length === 0 ? (
        <div className="card p-10 text-center text-gray-500">Aucun PDF publié.</div>
      ) : (
        <div className="flex flex-col gap-3">
          {pdfs.map((p) => (
            <div key={p.id} className="card flex items-center gap-4 p-4">
              <div className="grid h-14 w-14 shrink-0 place-items-center rounded-lg bg-amber-50 text-amber-600">
                <FileText size={22} />
              </div>
              <div className="flex-1">
                <p className="font-semibold">{p.title}</p>
                <p className="text-xs text-gray-500">{p.page_count} pages · {formatPrice(p.price)} · <Download size={12} className="inline" /> {p.downloads_count}</p>
              </div>
              {p.file && <PdfViewer url={p.file} title={p.title} />}
              <span className={`badge ${p.published ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-600"}`}>
                {p.published ? "Publié" : "Brouillon"}
              </span>
              <button onClick={() => togglePublished(p)} className="btn-outline !py-1.5 !text-xs">
                {p.published ? <EyeOff size={14} /> : <Eye size={14} />} {p.published ? "Dépublier" : "Publier"}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
