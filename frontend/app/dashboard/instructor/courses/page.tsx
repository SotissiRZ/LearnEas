"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { PlusCircle, Users, PlayCircle, Pencil, Search, Eye, EyeOff, Trash2, ExternalLink, Settings2 } from "lucide-react";
import { api, ApiError, formatDuration } from "@/lib/api";
import { Course } from "@/types";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import GuardScreen from "@/components/ui/GuardScreen";

export default function InstructorCoursesPage() {
  const { ready } = useAuthGuard({ roles: ["instructor", "admin"], redirectTo: "/dashboard/instructor" });
  const [courses, setCourses] = useState<Course[]>([]); const [loading, setLoading] = useState(true); const [search, setSearch] = useState(""); const [status, setStatus] = useState("all"); const [message, setMessage] = useState("");
  async function load(){const d=await api.get<{results:Course[]}|Course[]>("/catalog/courses/my_courses/");setCourses(Array.isArray(d)?d:d.results);setLoading(false)}
  useEffect(()=>{if(ready)load().catch(()=>setLoading(false))},[ready]);
  const filtered=useMemo(()=>courses.filter(c=>(status==="all"||(status==="published"?c.published:!c.published))&&(!search.trim()||`${c.title} ${c.subtitle||""}`.toLowerCase().includes(search.toLowerCase()))),[courses,search,status]);
  async function toggle(c:Course){setMessage("");try{await api.patch(`/catalog/courses/${c.slug}/`,{published:!c.published});await load()}catch(e){setMessage(e instanceof ApiError?e.message:"Impossible de modifier la publication.")}}
  async function remove(c:Course){if(!confirm(`Supprimer définitivement le cours « ${c.title} » et ses contenus ?`))return;setMessage("");try{await api.del(`/catalog/courses/${c.slug}/`);await load();setMessage("Cours supprimé.")}catch(e){setMessage(e instanceof ApiError?e.message:"Impossible de supprimer le cours.")}}
  if(!ready)return <GuardScreen/>;
  return <div className="min-w-0"><div className="mb-6 flex flex-wrap items-start justify-between gap-3"><div><h1 className="text-xl font-bold">Mes cours</h1><p className="mt-1 text-sm text-gray-500">Créez, modifiez, publiez et organisez vos playlists pédagogiques.</p></div><Link href="/dashboard/instructor/courses/new" className="btn-primary !py-2 !text-sm"><PlusCircle size={16}/> Nouveau cours</Link></div>
    <div className="card mb-4 flex flex-wrap gap-3 p-4"><div className="relative min-w-[220px] flex-1"><Search size={15} className="absolute left-3 top-2.5 text-gray-400"/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Rechercher un cours" className="w-full rounded-lg border border-gray-200 py-2 pl-9 pr-3 text-sm"/></div><select value={status} onChange={e=>setStatus(e.target.value)} className="rounded-lg border border-gray-200 px-3 py-2 text-sm"><option value="all">Tous les statuts</option><option value="published">Publiés</option><option value="draft">Brouillons</option></select></div>
    {message&&<div className="mb-4 rounded-xl bg-gray-50 p-3 text-sm text-gray-600">{message}</div>}
    {loading?<div className="card p-8 text-center text-gray-500">Chargement...</div>:filtered.length===0?<div className="card p-10 text-center text-gray-500">Aucun cours correspondant.</div>:<div className="flex flex-col gap-3">{filtered.map(c=><div key={c.id} className="card flex flex-wrap items-center gap-4 p-4"><div className="flex h-16 w-24 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-gray-100">{c.thumbnail?<img src={c.thumbnail} alt={c.title} className="h-full w-full object-cover"/>:<PlayCircle className="text-gray-300"/>}</div><div className="min-w-[220px] flex-1"><p className="font-semibold">{c.title}</p><p className="text-xs text-gray-500">{c.total_lessons} vidéos · {formatDuration(c.total_duration_minutes)} · <Users size={12} className="inline"/> {c.students_count} étudiant(s)</p></div><span className={`badge ${c.published?"bg-emerald-50 text-emerald-700":"bg-gray-100 text-gray-600"}`}>{c.published?"Publié":"Brouillon"}</span><div className="flex flex-wrap gap-2"><Link href={`/courses/${c.slug}`} target="_blank" className="btn-outline !px-2.5 !py-1.5 !text-xs"><ExternalLink size={13}/> Voir</Link><Link href={`/dashboard/instructor/courses/${c.id}/edit`} className="btn-outline !px-2.5 !py-1.5 !text-xs"><Pencil size={13}/> Modifier</Link><Link href={`/dashboard/instructor/courses/${c.id}`} className="btn-outline !px-2.5 !py-1.5 !text-xs"><Settings2 size={13}/> Contenu</Link><button onClick={()=>toggle(c)} className="btn-outline !px-2.5 !py-1.5 !text-xs">{c.published?<EyeOff size={13}/>:<Eye size={13}/>} {c.published?"Dépublier":"Publier"}</button><button onClick={()=>remove(c)} className="rounded-lg border border-red-100 px-2.5 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50"><Trash2 size={13} className="mr-1 inline"/>Supprimer</button></div></div>)}</div>}
  </div>;
}
