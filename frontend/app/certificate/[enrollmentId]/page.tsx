"use client";
import { useEffect,useState } from "react";
import { useParams } from "next/navigation";
import { api,ApiError } from "@/lib/api";
import type { Certificate } from "@/types";
import CertificateCard from "@/components/ui/CertificateCard";
import GuardScreen from "@/components/ui/GuardScreen";
import { useAuthGuard } from "@/hooks/useAuthGuard";
export default function LegacyCertificate(){const {ready}=useAuthGuard(); const {enrollmentId}=useParams<{enrollmentId:string}>(); const [cert,setCert]=useState<Certificate|null>(null);const [error,setError]=useState("");useEffect(()=>{if(ready)api.get<Certificate>(`/enrollments/my-courses/${enrollmentId}/certificate/`).then(setCert).catch(e=>setError(e instanceof ApiError?e.message:"Certificat indisponible."));},[ready,enrollmentId]);if(!ready)return <GuardScreen/>;if(error)return <div className="container-app py-16 text-center text-red-600">{error}</div>;if(!cert)return <div className="container-app py-16 text-center text-gray-400">Chargement...</div>;return <div className="container-app py-12"><CertificateCard certificate={cert}/></div>}
