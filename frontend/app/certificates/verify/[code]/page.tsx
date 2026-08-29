"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { AlertTriangle, ShieldCheck } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { Certificate } from "@/types";
import CertificateCard from "@/components/ui/CertificateCard";

export default function VerifyCertificatePage(){
  const { code } = useParams<{code:string}>(); const [cert,setCert]=useState<Certificate|null>(null); const [error,setError]=useState("");
  useEffect(()=>{api.get<Certificate>(`/enrollments/certificates/verify/${code}/`).then(setCert).catch(e=>setError(e instanceof ApiError?e.message:"Certificat introuvable."));},[code]);
  if(error) return <div className="container-app max-w-2xl py-16"><div className="card p-8 text-center text-red-600"><AlertTriangle className="mx-auto"/><h1 className="mt-3 text-xl font-bold">Vérification impossible</h1><p className="mt-2 text-sm">{error}</p></div></div>;
  if(!cert) return <div className="container-app py-16 text-center text-gray-400">Vérification du certificat...</div>;
  return <div className="container-app py-12"><div className="mb-6 text-center"><ShieldCheck className="mx-auto text-brand-600"/><h1 className="mt-2 text-2xl font-bold">Résultat de la vérification</h1><p className="text-sm text-gray-500">Le registre LearnEas confirme les informations affichées ci-dessous.</p></div><CertificateCard certificate={cert} publicMode /></div>;
}
