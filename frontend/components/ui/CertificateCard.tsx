"use client";

import {
  AlertTriangle,
  Award,
  CheckCircle2,
  Copy,
  Download,
  ClipboardCheck,
  ExternalLink,
  FileCheck2,
  Fingerprint,
  Printer,
  QrCode,
  Share2,
  ShieldCheck,
} from "lucide-react";
import type { Certificate } from "@/types";
import { useState } from "react";

export default function CertificateCard({ certificate, publicMode = false }: { certificate: Certificate; publicMode?: boolean }) {
  const status = certificate.effective_status || certificate.status;
  const valid = status === "active";
  const [copied, setCopied] = useState(false);
  const [cvCopied, setCvCopied] = useState(false);
  const verificationUrl = certificate.verification_url || (typeof window !== "undefined" ? `${window.location.origin}/certificates/verify/${certificate.verification_code}` : "");
  const skills = certificate.skills_snapshot || [];
  const projects = certificate.projects_snapshot || [];

  async function copyVerificationLink() {
    if (!verificationUrl) return;
    try {
      await navigator.clipboard.writeText(verificationUrl);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1800);
    } catch { /* presse-papiers indisponible */ }
  }


  async function copyCvEntry() {
    const entry = certificate.cv_entry;
    if (!entry) return;
    const lines = [
      `${entry.title} — ${entry.issuer}`,
      `Identifiant : ${entry.credential_id}`,
      entry.issued_at ? `Émis le : ${new Date(`${entry.issued_at}T00:00:00`).toLocaleDateString("fr-FR")}` : "",
      entry.expires_at ? `Expire le : ${new Date(`${entry.expires_at}T00:00:00`).toLocaleDateString("fr-FR")}` : "",
      entry.skills?.length ? `Compétences : ${entry.skills.join(", ")}` : "",
      `Vérification : ${entry.verification_url}`,
    ].filter(Boolean).join("\n");
    try {
      await navigator.clipboard.writeText(lines);
      setCvCopied(true);
      window.setTimeout(() => setCvCopied(false), 1800);
    } catch { /* presse-papiers indisponible */ }
  }

  async function shareCertificate() {
    if (!verificationUrl) return;
    try {
      if (navigator.share) await navigator.share({ title: certificate.title || "Certificat KalanPro", text: `${certificate.student_name} · ${certificate.content_title}`, url: verificationUrl });
      else await copyVerificationLink();
    } catch { /* partage annulé */ }
  }

  return (
    <div className="w-full">
      <div className="mb-4 flex flex-wrap justify-end gap-2 print:hidden">
        {!publicMode && <button onClick={() => window.print()} className="btn-primary"><Printer size={16}/> Imprimer</button>}
        {certificate.pdf_url && <a href={certificate.pdf_url} className="btn-primary"><Download size={16}/> Télécharger PDF</a>}
        {!publicMode && <button onClick={copyCvEntry} className="btn-outline"><ClipboardCheck size={16}/> {cvCopied ? "Entrée CV copiée" : "Copier pour mon CV"}</button>}
        <button onClick={copyVerificationLink} className="btn-outline"><Copy size={16}/> {copied ? "Lien copié" : "Copier le lien"}</button>
        <button onClick={shareCertificate} className="btn-outline"><Share2 size={16}/> Partager</button>
        {verificationUrl && <a href={verificationUrl} target="_blank" rel="noreferrer" className="btn-outline"><ExternalLink size={16}/> Vérifier</a>}
      </div>

      {!valid && <div className={`mx-auto mb-4 max-w-4xl rounded-2xl border p-4 ${status === "revoked" ? "border-red-200 bg-red-50 text-red-800" : "border-amber-200 bg-amber-50 text-amber-800"}`}>
        <div className="flex items-start gap-3"><AlertTriangle className="mt-0.5 shrink-0" size={20}/><div><p className="font-bold">{status === "revoked" ? "Ce certificat a été révoqué" : "Ce certificat a expiré"}</p><p className="mt-1 text-sm">Le QR code et le numéro restent consultables afin de préserver l'historique du registre.</p>{!publicMode && certificate.revocation_reason && <p className="mt-2 text-xs">Motif interne : {certificate.revocation_reason}</p>}{certificate.replacement_verification_url && <a className="mt-2 inline-flex items-center gap-1 text-sm font-semibold underline" href={certificate.replacement_verification_url}>Voir la version de remplacement <ExternalLink size={13}/></a>}</div></div>
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

        <div className="mx-auto mt-7 grid max-w-3xl gap-3 text-sm sm:grid-cols-2 lg:grid-cols-4">
          {certificate.display_options?.show_instructor !== false && <Info label="Instructeur" value={certificate.instructor_name || "-"} />}
          <Info label="Émetteur" value={certificate.issuer_name || "KalanPro"} />
          {certificate.display_options?.show_duration !== false && <Info label="Durée" value={`${Math.round((certificate.duration_minutes || 0) / 60 * 10) / 10} h`} />}
          <Info label="Résultat" value={`${Number(certificate.achievement_percent || 0).toFixed(0)} %`} />
        </div>

        {skills.length > 0 && <div className="mx-auto mt-7 max-w-3xl text-left">
          <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-gray-400">Compétences attestées</p>
          <div className="mt-2 flex flex-wrap gap-2">{skills.map((skill) => <span key={skill} className="rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-700">{skill}</span>)}</div>
        </div>}

        {projects.length > 0 && <div className="mx-auto mt-7 max-w-3xl text-left">
          <div className="mb-2 flex items-center gap-2 text-[10px] font-bold uppercase tracking-[0.16em] text-gray-400"><FileCheck2 size={14}/> Projets pratiques validés</div>
          <div className="space-y-2">{projects.map((project, index) => <div key={`${project.title}-${index}`} className="rounded-xl border border-gray-100 p-3 text-sm">
            <div className="flex flex-wrap items-start justify-between gap-2"><div><p className="font-semibold text-ink">{project.title}</p>{project.validated_by && <p className="mt-0.5 text-xs text-gray-400">Validé par {project.validated_by}{project.validated_at ? ` · ${new Date(project.validated_at).toLocaleDateString("fr-FR")}` : ""}</p>}</div>{project.score != null && <span className="badge bg-emerald-50 text-emerald-700">{project.score}/{project.max_score || 100}</span>}</div>
          </div>)}</div>
        </div>}

        {(certificate.signatory_name || certificate.signatory_title) && <div className="mx-auto mt-10 max-w-xs border-t border-gray-300 pt-2"><p className="font-semibold">{certificate.signatory_name}</p><p className="text-xs text-gray-400">{certificate.signatory_title}</p></div>}

        <div className="mt-10 grid items-center gap-5 border-t border-gray-100 pt-5 text-left sm:grid-cols-[1fr_auto]">
          <div className="space-y-2 text-[11px] text-gray-500">
            <p>{certificate.display_options?.show_completion_date !== false && certificate.completed_at ? `Validé le ${new Date(certificate.completed_at).toLocaleDateString("fr-FR")}` : `Délivré le ${new Date(certificate.issued_at).toLocaleDateString("fr-FR")}`}</p>
            <p className="font-semibold text-gray-700">N° {certificate.certificate_number}</p>
            <p className="flex items-start gap-1"><CheckCircle2 size={11} className="mt-0.5 shrink-0"/> Code : <span className="break-all">{certificate.verification_code}</span></p>
            {certificate.issuer_country && <p>Émetteur : {certificate.issuer_name || "KalanPro"} · {certificate.issuer_country}</p>}
            {certificate.supersedes_certificate_number && <p>Remplace : {certificate.supersedes_certificate_number}</p>}
            {certificate.expires_at && <p>Expiration : {new Date(certificate.expires_at).toLocaleDateString("fr-FR")}</p>}
          </div>
          {certificate.qr_url && <div className="justify-self-center rounded-xl border border-gray-100 bg-white p-2 text-center">
            <img src={certificate.qr_url} alt="QR code de vérification du certificat" className="h-28 w-28" loading="lazy" decoding="async" />
            <p className="mt-1 flex items-center justify-center gap-1 text-[9px] font-semibold uppercase tracking-wide text-gray-400"><QrCode size={10}/> Scanner pour vérifier</p>
          </div>}
        </div>

        {certificate.credential_digest && <div className="mt-4 flex items-start justify-center gap-1 text-[9px] text-gray-400"><Fingerprint size={11} className="mt-0.5 shrink-0"/><span>Empreinte SHA-256 : <span className="break-all font-mono">{certificate.credential_digest}</span></span></div>}
      </div>

      {!publicMode && certificate.events && certificate.events.length > 0 && <div className="mx-auto mt-6 max-w-4xl card p-5 print:hidden">
        <h3 className="flex items-center gap-2 font-bold"><ShieldCheck size={17}/> Historique du registre</h3>
        <div className="mt-3 divide-y divide-gray-100">{certificate.events.map((event) => <div key={event.id} className="flex flex-wrap justify-between gap-2 py-3 text-sm"><div><p className="font-semibold capitalize">{eventLabel(event.event_type)}</p><p className="text-xs text-gray-400">{event.actor_name}</p></div><span className="text-xs text-gray-400">{new Date(event.created_at).toLocaleString("fr-FR")}</span></div>)}</div>
      </div>}
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return <div className="rounded-xl bg-gray-50 p-3"><p className="text-[10px] uppercase tracking-wide text-gray-400">{label}</p><p className="mt-1 font-semibold text-ink">{value}</p></div>;
}

function eventLabel(type: "issued" | "revoked" | "reissued" | "expired") {
  if (type === "issued") return "Certificat émis";
  if (type === "revoked") return "Certificat révoqué";
  if (type === "reissued") return "Certificat réémis";
  return "Certificat expiré";
}
