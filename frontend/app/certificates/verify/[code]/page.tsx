"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AlertTriangle, CheckCircle2, Clock3, Search, ShieldCheck, ShieldX } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { Certificate } from "@/types";
import CertificateCard from "@/components/ui/CertificateCard";

export default function VerifyCertificatePage(){
  const { code } = useParams<{code:string}>();
  const [cert,setCert]=useState<Certificate|null>(null);
  const [error,setError]=useState("");

  useEffect(()=>{
    api.get<Certificate>(`/enrollments/certificates/verify/${code}/`).then(setCert).catch(e=>setError(e instanceof ApiError?e.message:"Certificat introuvable."));
  },[code]);

  if(error) return <div className="container-app max-w-2xl py-16"><div className="card p-8 text-center text-red-600"><AlertTriangle className="mx-auto"/><h1 className="mt-3 text-xl font-bold">Vérification impossible</h1><p className="mt-2 text-sm">{error}</p><Link href="/certificates/verify" className="btn-outline mt-5"><Search size={15}/> Nouvelle recherche</Link></div></div>;
  if(!cert) return <div className="container-app py-16 text-center text-gray-400">Vérification du certificat...</div>;

  const status=cert.effective_status;
  return <div className="container-app py-12">
    <div className="mx-auto mb-6 max-w-4xl text-center">
      {status==="active"?<CheckCircle2 className="mx-auto text-emerald-600" size={38}/>:status==="revoked"?<ShieldX className="mx-auto text-red-600" size={38}/>:<Clock3 className="mx-auto text-amber-600" size={38}/>}      
      <h1 className="mt-2 text-2xl font-bold">{status==="active"?"Certificat authentique et valide":status==="revoked"?"Certificat authentique mais révoqué":"Certificat authentique mais expiré"}</h1>
      <p className="mt-2 text-sm text-gray-500">Le registre public LearnEas confirme l'identité du détenteur, le contenu suivi et les preuves figées lors de l'émission.</p>
      <div className="mt-3 inline-flex items-center gap-2 rounded-full bg-gray-50 px-3 py-1 text-xs font-semibold text-gray-600"><ShieldCheck size={13}/> N° {cert.certificate_number}</div>
    </div>
    <CertificateCard certificate={cert} publicMode />
    <div className="mx-auto mt-6 max-w-4xl text-center print:hidden"><Link href="/certificates/verify" className="btn-outline"><Search size={15}/> Vérifier un autre certificat</Link></div>
  </div>;
}
