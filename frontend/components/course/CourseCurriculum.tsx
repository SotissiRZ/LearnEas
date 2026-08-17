"use client";

import { useState } from "react";
import { PlayCircle, Lock, ChevronDown, FileText, Download, Clock } from "lucide-react";
import { Section, PDFResource } from "@/types";
import { formatDuration } from "@/lib/api";
import PdfViewer from "@/components/ui/PdfViewer";

export default function CourseCurriculum({
  sections,
  pdfResources,
}: {
  sections: Section[];
  pdfResources: PDFResource[];
}) {
  const [open, setOpen] = useState<number | null>(sections[0]?.id ?? null);

  return (
    <div className="flex flex-col gap-6">
      <div className="card divide-y divide-gray-100 overflow-hidden">
        {sections.map((section) => (
          <div key={section.id}>
            <button
              onClick={() => setOpen(open === section.id ? null : section.id)}
              className="flex w-full items-center justify-between gap-4 p-4 text-left hover:bg-gray-50"
            >
              <div>
                <p className="font-semibold text-ink">{section.title}</p>
                <p className="text-xs text-gray-500">
                  {section.lessons.length} vidéos · {formatDuration(section.duration_minutes)}
                </p>
              </div>
              <ChevronDown
                size={18}
                className={`shrink-0 text-gray-400 transition-transform ${open === section.id ? "rotate-180" : ""}`}
              />
            </button>
            {open === section.id && (
              <div className="divide-y divide-gray-50 bg-gray-50/50">
                {section.lessons.map((lesson) => (
                  <div key={lesson.id} className="flex items-center gap-3 px-4 py-3 text-sm">
                    {lesson.locked ? (
                      <Lock size={16} className="shrink-0 text-gray-400" />
                    ) : (
                      <PlayCircle size={16} className="shrink-0 text-brand-600" />
                    )}
                    <span className={`flex-1 ${lesson.locked ? "text-gray-500" : "text-ink"}`}>{lesson.title}</span>
                    {lesson.is_preview && (
                      <span className="badge bg-brand-50 text-brand-700">Aperçu gratuit</span>
                    )}
                    <span className="flex items-center gap-1 text-xs text-gray-400">
                      <Clock size={12} /> {formatDuration(lesson.duration_minutes)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {pdfResources.length > 0 && (
        <div className="card p-5">
          <h3 className="mb-3 flex items-center gap-2 font-bold">
            <FileText size={18} className="text-amber-600" /> Ressources PDF incluses
          </h3>
          <div className="flex flex-col gap-2">
            {pdfResources.map((pdf) => (
              <div key={pdf.id} className="flex items-center justify-between rounded-lg border border-gray-100 px-3 py-2 text-sm">
                <div className="flex items-center gap-2">
                  {pdf.locked ? <Lock size={14} className="text-gray-400" /> : <FileText size={14} className="text-amber-600" />}
                  <span className={pdf.locked ? "text-gray-500" : "text-ink"}>{pdf.title}</span>
                  <span className="text-xs text-gray-400">({pdf.page_count} pages)</span>
                </div>
                {!pdf.locked && pdf.file && <PdfViewer url={pdf.file} title={pdf.title} />}
                {pdf.is_free_sample && <span className="badge bg-brand-50 text-brand-700">Extrait gratuit</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
