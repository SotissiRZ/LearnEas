"use client";
import { useEffect,useState } from "react";
import { useParams } from "next/navigation";
import { api,ApiError } from "@/lib/api";
import type { Certificate } from "@/types";
import CertificateCard from "@/components/ui/CertificateCard";
import GuardScreen from "@/components/ui/GuardScreen";
import { useAuthGuard } from "@/hooks/useAuthGuard";
export default function CertificateDetail(){const {ready}=useAuthGuard(); const {id}=useParams<{id:string}>(); const [cert,setCert]=useState<Certificate|null>(null);const [error,setError]=useState("");useEffect(()=>{if(ready) api.get<Certificate>(`/enrollments/certificates/${id}/`).then(setCert).catch(e=>setError(e instanceof ApiError?e.message:"Certificat indisponible."));},[ready,id]); if(!ready)return <GuardScreen/>; if(error)return <div className="container-app py-16 text-center text-red-600">{error}</div>; if(!cert)return <div className="container-app py-16 text-center text-gray-400">Chargement...</div>; return <div className="container-app py-12"><CertificateCard certificate={cert}/></div>}
