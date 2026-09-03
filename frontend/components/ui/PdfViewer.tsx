"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Download, ExternalLink, FileText, Maximize2, Minimize2, Printer, X } from "lucide-react";
import { resolveMediaUrl } from "@/lib/media";

export default function PdfViewer({ url, title = "Document PDF" }: { url: string; title?: string }) {
  const resolvedUrl = useMemo(() => resolveMediaUrl(url), [url]);
  const [open, setOpen] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const readerRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const handler = () => setFullscreen(Boolean(document.fullscreenElement));
    document.addEventListener("fullscreenchange", handler);
    return () => document.removeEventListener("fullscreenchange", handler);
  }, []);

  function printPdf() {
    const win = window.open(resolvedUrl, "_blank");
    if (win) {
      try { win.opener = null; } catch { /* noop */ }
      window.setTimeout(() => { try { win.print(); } catch { /* le lecteur natif garde son bouton Imprimer */ } }, 900);
    }
  }

  async function toggleFullscreen() {
    try {
      if (document.fullscreenElement) await document.exitFullscreen();
      else await readerRef.current?.requestFullscreen();
    } catch { /* API plein écran indisponible */ }
  }

  return (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <button onClick={() => setOpen(true)} className="btn-outline !py-1.5 !text-xs">
          <Maximize2 size={14} /> Lire
        </button>
        <a href={resolvedUrl} target="_blank" rel="noreferrer" className="btn-outline !py-1.5 !text-xs" title="Ouvrir avec toutes les fonctions du lecteur PDF du navigateur">
          <ExternalLink size={14} /> Nouvel onglet
        </a>
        <a href={resolvedUrl} download className="btn-outline !py-1.5 !text-xs"><Download size={14} /> Télécharger</a>
      </div>

      {open && (
        <div className="fixed inset-0 z-50 flex flex-col bg-black/80 p-2 sm:p-5" onClick={() => setOpen(false)}>
          <div ref={readerRef} className="mx-auto flex h-full w-full max-w-6xl flex-col overflow-hidden rounded-xl2 bg-white" onClick={(e) => e.stopPropagation()}>
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-100 p-3">
              <span className="flex min-w-0 items-center gap-2 text-sm font-semibold"><FileText size={16} className="shrink-0 text-amber-600" /><span className="truncate">{title}</span></span>
              <div className="flex flex-wrap items-center gap-2">
                <span className="hidden text-[11px] text-gray-400 md:inline">Recherche, pages, zoom et miniatures sont disponibles dans la barre native du lecteur.</span>
                <button onClick={printPdf} className="btn-outline !py-1 !text-xs"><Printer size={14} /> Imprimer</button>
                <button onClick={toggleFullscreen} className="btn-outline !py-1 !text-xs">{fullscreen ? <Minimize2 size={14} /> : <Maximize2 size={14} />} {fullscreen ? "Quitter plein écran" : "Plein écran"}</button>
                <a href={resolvedUrl} target="_blank" rel="noreferrer" className="btn-outline !py-1 !text-xs"><ExternalLink size={14} /> Nouvel onglet</a>
                <a href={resolvedUrl} download className="btn-outline !py-1 !text-xs"><Download size={14} /> Télécharger</a>
                <button onClick={() => setOpen(false)} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700" aria-label="Fermer le lecteur"><X size={18} /></button>
              </div>
            </div>
            <iframe src={`${resolvedUrl}#toolbar=1&navpanes=1&scrollbar=1&view=FitH`} title={title} className="min-h-0 flex-1 bg-gray-100" />
          </div>
        </div>
      )}
    </>
  );
}
