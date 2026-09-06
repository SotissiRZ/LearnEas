"use client";

import Link from "next/link";
import { Flag } from "lucide-react";

type Props={targetType:string;targetId:string|number;label:string;url?:string;className?:string};
export default function ReportLink({targetType,targetId,label,url,className=""}:Props){
  const q=new URLSearchParams({view:"reports",target_type:targetType,target_id:String(targetId),target_label:label});
  if(url)q.set("target_url",url);
  return <Link href={`/support?${q.toString()}`} className={`inline-flex items-center gap-1.5 text-xs font-semibold text-gray-400 hover:text-red-600 ${className}`}><Flag size={13}/>Signaler</Link>
}
