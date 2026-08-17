"use client";

import { useState } from "react";
import { FileText, Download, X, Maximize2 } from "lucide-react";

/**
 * Lecteur PDF intégré : ouvre le fichier dans une modale plein écran via le lecteur PDF natif
 * du navigateur (iframe), qui fournit nativement zoom, navigation de pages, recherche et
 * impression — sans dépendance externe. Le téléchargement reste possible via le bouton dédié.
 */
export default function PdfViewer({ url, title }: { url: string; title: string }) {
  const [open, setOpen] = useState(false);

  return (
    <>
      <div className="flex items-center gap-2">
        <button onClick={() => setOpen(true)} className="btn-outline !py-1.5 !text-xs">
          <Maximize2 size={14} /> Aperçu
        </button>
        <a href={url} download target="_blank" rel="noreferrer" className="btn-outline !py-1.5 !text-xs">
          <Download size={14} /> Télécharger
        </a>
      </div>

      {open && (
        <div className="fixed inset-0 z-50 flex flex-col bg-black/80 p-2 sm:p-6" onClick={() => setOpen(false)}>
          <div
            className="mx-auto flex h-full w-full max-w-5xl flex-col overflow-hidden rounded-xl2 bg-white"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-gray-100 p-3">
              <span className="flex items-center gap-2 text-sm font-semibold">
                <FileText size={16} className="text-amber-600" /> {title}
              </span>
              <div className="flex items-center gap-2">
                <a href={url} download target="_blank" rel="noreferrer" className="btn-outline !py-1 !text-xs">
                  <Download size={14} /> Télécharger
                </a>
                <button onClick={() => setOpen(false)} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-700">
                  <X size={18} />
                </button>
              </div>
            </div>
            <iframe src={url} title={title} className="flex-1" />
          </div>
        </div>
      )}
    </>
  );
}
