"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Building2, BriefcaseBusiness, PlusCircle, Users } from "lucide-react";
const links=[
  {href:"/dashboard/employer",label:"Entreprise",icon:<Building2 size={16}/>},
  {href:"/dashboard/employer/opportunities/new",label:"Nouvelle opportunité",icon:<PlusCircle size={16}/>},
  {href:"/dashboard/employer/applications",label:"Candidatures",icon:<Users size={16}/>},
];
export default function EmployerNav(){const p=usePathname();return <div className="mb-7 flex flex-wrap gap-2 border-b border-gray-100 pb-4">{links.map(l=><Link key={l.href} href={l.href} className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium ${p===l.href?"bg-brand-50 text-brand-700":"text-gray-600 hover:bg-gray-50"}`}>{l.icon}{l.label}</Link>)}<Link href="/opportunities" className="ml-auto flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-gray-500 hover:bg-gray-50"><BriefcaseBusiness size={16}/> Marketplace</Link></div>}
