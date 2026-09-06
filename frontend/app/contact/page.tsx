"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { LifeBuoy, Mail } from "lucide-react";
import { api } from "@/lib/api";

export default function ContactPage() {
  const [supportEmail, setSupportEmail] = useState("support@kalanpro.com");
  useEffect(() => { api.get<{ support_email: string }>("/auth/platform-settings/").then((data) => data.support_email && setSupportEmail(data.support_email)).catch(() => undefined); }, []);
  return <div className="container-app max-w-2xl py-16"><div className="card p-6 sm:p-8"><h1 className="flex items-center gap-2 text-3xl font-extrabold"><LifeBuoy className="text-brand-600"/>Besoin d’aide ?</h1><p className="mt-3 text-gray-500">Pour un suivi fiable, créez un ticket : vous pourrez voir le statut et échanger avec le support depuis KalanPro.</p><div className="mt-6 flex flex-wrap gap-3"><Link href="/support" className="btn-primary"><LifeBuoy size={16}/>Ouvrir le centre de support</Link><a className="btn-outline" href={`mailto:${supportEmail}`}><Mail size={16}/>Email : {supportEmail}</a></div></div></div>;
}
