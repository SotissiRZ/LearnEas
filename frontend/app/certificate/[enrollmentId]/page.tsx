"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { Award, Printer, GraduationCap } from "lucide-react";
import { api } from "@/lib/api";

interface CertificateData {
  student_name: string;
  course_title: string;
  instructor_name: string;
  completed_at: string;
  total_hours: number;
  certificate_id: string;
}

export default function CertificatePage() {
  const params = useParams<{ enrollmentId: string }>();
  const [data, setData] = useState<CertificateData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get<CertificateData>(`/enrollments/my-courses/${params.enrollmentId}/certificate/`)
      .then(setData)
      .catch((e) => setError(e.message || "Certificat indisponible."));
  }, [params.enrollmentId]);

  if (error) {
    return <div className="container-app py-20 text-center text-gray-500">{error}</div>;
  }
  if (!data) {
    return <div className="container-app py-20 text-center text-gray-500">Chargement du certificat...</div>;
  }

  return (
    <div className="container-app flex flex-col items-center gap-6 py-14">
      <div className="print:hidden">
        <button onClick={() => window.print()} className="btn-primary">
          <Printer size={16} /> Imprimer / Enregistrer en PDF
        </button>
      </div>

      <div className="relative w-full max-w-3xl border-8 border-double border-brand-700 bg-white p-12 text-center shadow-soft print:border-4 print:shadow-none">
        <div className="mb-6 flex flex-col items-center gap-2">
          <div className="grid h-14 w-14 place-items-center rounded-2xl bg-brand-600 text-white">
            <GraduationCap size={28} />
          </div>
          <p className="text-lg font-extrabold tracking-wide">
            Learn<span className="text-brand-600">Eas</span>
          </p>
        </div>

        <Award className="mx-auto mb-4 text-amber-500" size={40} />
        <p className="text-sm uppercase tracking-widest text-gray-500">Certificat de fin de formation</p>
        <h1 className="mt-4 text-3xl font-extrabold text-ink">{data.student_name}</h1>
        <p className="mt-4 text-gray-600">a suivi et validé avec succès le cours</p>
        <h2 className="mt-2 text-xl font-bold text-brand-700">{data.course_title}</h2>
        <p className="mt-4 text-sm text-gray-500">
          {data.total_hours} heures de formation — encadré par {data.instructor_name}
        </p>

        <div className="mt-10 flex items-center justify-between text-xs text-gray-400">
          <span>Délivré le {new Date(data.completed_at).toLocaleDateString("fr-FR")}</span>
          <span>N° {data.certificate_id}</span>
        </div>
      </div>
    </div>
  );
}
