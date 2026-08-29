"use client";

import { Award, CheckCircle2, Copy, ExternalLink, Printer, Share2, ShieldCheck } from "lucide-react";
import type { Certificate } from "@/types";
import { useState } from "react";

export default function CertificateCard({ certificate, publicMode = false }: { certificate: Certificate; publicMode?: boolean }) {
  const status = certificate.effective_status || certificate.status;
  const valid = status === "active";
  const [copied, setCopied] = useState(false);
  const verificationUrl = certificate.verification_url || (typeof window !== "undefined" ? `${window.location.origin}/certificates/verify/${certificate.verification_code}` : "");

  async function copyVerificationLink() {
    if (!verificationUrl) return;
    try { await navigator.clipboard.writeText(verificationUrl); setCopied(true); window.setTimeout(() => setCopied(false), 1800); } catch { /* presse-papiers indisponible */ }
  }

  async function shareCertificate() {
    if (!verificationUrl) return;
    try {
      if (navigator.share) await navigator.share({ title: certificate.title || "Certificat LearnEas", text: `${certificate.student_name} — ${certificate.content_title}`, url: verificationUrl });
      else await copyVerificationLink();
    } catch { /* partage annulé */ }
  }

  return (
    <div className="w-full">
      {!publicMode && <div className="mb-4 flex flex-wrap justify-end gap-2 print:hidden">
        <button onClick={() => window.print()} className="btn-primary"><Printer size={16}/> Imprimer / Enregistrer en PDF</button>
        <button onClick={copyVerificationLink} className="btn-outline"><Copy size={16}/> {copied ? "Lien copié" : "Copier le lien"}</button>
        <button onClick={shareCertificate} className="btn-outline"><Share2 size={16}/> Partager</button>
        {verificationUrl && <a href={verificationUrl} target="_blank" rel="noreferrer" className="btn-outline"><ExternalLink size={16}/> Vérifier</a>}
      </div>}
      <div className="relative mx-auto w-full max-w-4xl overflow-hidden border-[10px] border-double bg-white p-8 text-center shadow-soft print:border-4 print:shadow-none sm:p-12" style={{ borderColor: certificate.accent_color || "#1f6f5c" }}>
        <div className="absolute right-4 top-4 flex items-center gap-1 rounded-full border border-gray-100 bg-white px-2 py-1 text-[10px] font-semibold text-gray-500"><ShieldCheck size={12}/>{valid ? "Vérifié" : status === "revoked" ? "Révoqué" : "Expiré"}</div>
        <Award className="mx-auto mb-4" size={44} style={{ color: certificate.accent_color || "#1f6f5c" }} />
        <p className="text-xs uppercase tracking-[0.28em] text-gray-500">{certificate.title || "Certificat"}</p>
        {certificate.subtitle && <p className="mt-2 text-sm text-gray-500">{certificate.subtitle}</p>}
        <h1 className="mt-7 text-3xl font-extrabold text-ink sm:text-4xl">{certificate.student_name}</h1>
        <p className="mt-4 text-gray-600">a satisfait aux critères de validation de</p>
        <h2 className="mt-2 text-xl font-bold" style={{ color: certificate.accent_color || "#1f6f5c" }}>{certificate.content_title}</h2>
        {certificate.description && <p className="mx-auto mt-4 max-w-2xl text-sm leading-6 text-gray-500">{certificate.description}</p>}
        <div className="mx-auto mt-7 grid max-w-2xl gap-3 text-sm sm:grid-cols-3">
          {certificate.display_options?.show_instructor !== false && <Info label="Instructeur" value={certificate.instructor_name || "—"} />}
          {certificate.display_options?.show_duration !== false && <Info label="Durée" value={`${Math.round((certificate.duration_minutes || 0) / 60 * 10) / 10} h`} />}
          <Info label="Résultat" value={`${Number(certificate.achievement_percent || 0).toFixed(0)} %`} />
        </div>
        {(certificate.signatory_name || certificate.signatory_title) && <div className="mx-auto mt-10 max-w-xs border-t border-gray-300 pt-2"><p className="font-semibold">{certificate.signatory_name}</p><p className="text-xs text-gray-400">{certificate.signatory_title}</p></div>}
        <div className="mt-10 flex flex-col justify-between gap-2 border-t border-gray-100 pt-4 text-[11px] text-gray-400 sm:flex-row">
          <span>{certificate.display_options?.show_completion_date !== false && certificate.completed_at ? `Validé le ${new Date(certificate.completed_at).toLocaleDateString("fr-FR")}` : `Délivré le ${new Date(certificate.issued_at).toLocaleDateString("fr-FR")}`}</span>
          <span>N° {certificate.certificate_number}</span>
        </div>
        <div className="mt-2 flex items-center justify-center gap-1 text-[10px] text-gray-400"><CheckCircle2 size={11}/> Code de vérification : {certificate.verification_code}</div>
        {certificate.expires_at && <p className="mt-1 text-[10px] text-gray-400">Expiration : {new Date(certificate.expires_at).toLocaleDateString("fr-FR")}</p>}
      </div>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) { return <div className="rounded-xl bg-gray-50 p-3"><p className="text-[10px] uppercase tracking-wide text-gray-400">{label}</p><p className="mt-1 font-semibold text-ink">{value}</p></div>; }
