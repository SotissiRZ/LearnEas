"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { ShieldCheck } from "lucide-react";
export default function VerifyLanding() {
  const [code,setCode]=useState(""); const router=useRouter();
  return <div className="container-app max-w-xl py-16"><div className="card p-8 text-center"><ShieldCheck className="mx-auto text-brand-600" size={38}/><h1 className="mt-3 text-2xl font-bold">Vérifier un certificat</h1><p className="mt-2 text-sm text-gray-500">Saisissez le code de vérification figurant sur le certificat.</p><form className="mt-6 flex gap-2" onSubmit={(e)=>{e.preventDefault(); if(code.trim()) router.push(`/certificates/verify/${code.trim()}`)}}><input className="input-admin flex-1" value={code} onChange={e=>setCode(e.target.value)} placeholder="Code UUID"/><button className="btn-primary">Vérifier</button></form></div></div>;
}
