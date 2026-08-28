"use client";

import { useEffect, useMemo, useState } from "react";
import { Star, MessageSquareText, Search, Send, Loader2 } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { Paginated } from "@/types";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import GuardScreen from "@/components/ui/GuardScreen";

interface PublicUser { id: number; full_name: string; }
interface Review { id: number; user: PublicUser; target_title: string; target_type: string; rating: number; comment: string; created_at: string; }
interface Comment { id: number; user: PublicUser; lesson: number; lesson_title: string; course_title: string; parent: number | null; content: string; created_at: string; replies: Comment[]; }

function unwrap<T>(d: Paginated<T> | T[]): T[] { return Array.isArray(d) ? d : d.results; }

export default function InstructorReviewsPage() {
  const { ready } = useAuthGuard({ roles: ["instructor", "admin"], redirectTo: "/dashboard/instructor" });
  const [reviews, setReviews] = useState<Review[]>([]); const [questions, setQuestions] = useState<Comment[]>([]); const [view, setView] = useState<"reviews"|"questions">("reviews"); const [search, setSearch] = useState(""); const [error, setError] = useState(""); const [loading, setLoading] = useState(true); const [replying, setReplying] = useState<number|null>(null); const [reply, setReply] = useState("");
  async function load(){ try { const [r,q]=await Promise.all([api.get<Paginated<Review>|Review[]>("/reviews/reviews/mine/?ordering=-created_at"), api.get<Paginated<Comment>|Comment[]>("/reviews/comments/mine/?ordering=-created_at")]); setReviews(unwrap(r)); setQuestions(unwrap(q)); } catch(e){setError(e instanceof ApiError?e.message:"Impossible de charger les avis et questions.");} finally{setLoading(false);} }
  useEffect(()=>{ if(ready) load(); },[ready]);
  useEffect(()=>{ if(typeof window!=="undefined" && new URLSearchParams(window.location.search).get("view")==="questions") setView("questions"); },[]);
  const reviewRows=useMemo(()=>reviews.filter(r=>!search.trim()||`${r.user.full_name} ${r.target_title} ${r.comment}`.toLowerCase().includes(search.toLowerCase())),[reviews,search]);
  const questionRows=useMemo(()=>questions.filter(q=>!search.trim()||`${q.user.full_name} ${q.course_title} ${q.lesson_title} ${q.content}`.toLowerCase().includes(search.toLowerCase())),[questions,search]);
  async function answer(q:Comment){ if(!reply.trim())return; setReplying(q.id); try{ await api.post("/reviews/comments/",{lesson:q.lesson,parent:q.id,content:reply}); setReply(""); await load(); } catch(e){setError(e instanceof ApiError?e.message:"Impossible d'envoyer la réponse.");} finally{setReplying(null);} }
  if(!ready)return <GuardScreen/>;
  return <div className="min-w-0"><div className="mb-6"><h1 className="text-xl font-bold">Avis & questions</h1><p className="mt-1 text-sm text-gray-500">Suivez la satisfaction et répondez aux questions posées sous vos leçons.</p></div>
    <div className="card mb-4 flex flex-wrap items-center gap-3 p-3"><button onClick={()=>setView("reviews")} className={`rounded-lg px-3 py-2 text-sm font-semibold ${view==="reviews"?"bg-brand-50 text-brand-700":"text-gray-500"}`}><Star size={14} className="mr-1 inline"/> Avis ({reviews.length})</button><button onClick={()=>setView("questions")} className={`rounded-lg px-3 py-2 text-sm font-semibold ${view==="questions"?"bg-brand-50 text-brand-700":"text-gray-500"}`}><MessageSquareText size={14} className="mr-1 inline"/> Questions ({questions.length})</button><div className="relative ml-auto min-w-[220px] flex-1 sm:max-w-xs"><Search size={14} className="absolute left-3 top-2.5 text-gray-400"/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Rechercher" className="w-full rounded-lg border border-gray-200 py-2 pl-9 pr-3 text-sm"/></div></div>
    {error&&<div className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</div>}{loading?<div className="card p-8 text-center text-gray-500">Chargement...</div>:view==="reviews"?<div className="grid gap-3">{reviewRows.map(r=><div key={r.id} className="card p-4"><div className="flex flex-wrap items-start justify-between gap-2"><div><p className="font-semibold">{r.user.full_name}</p><p className="text-xs text-gray-400">{r.target_title} · {r.target_type==="course"?"Cours":"PDF"}</p></div><span className="badge bg-amber-50 text-amber-700">{r.rating}/5 ★</span></div>{r.comment&&<p className="mt-3 text-sm leading-6 text-gray-600">{r.comment}</p>}<p className="mt-2 text-[11px] text-gray-400">{new Date(r.created_at).toLocaleString("fr-FR")}</p></div>)}{!reviewRows.length&&<Empty text="Aucun avis trouvé."/>}</div>:<div className="grid gap-3">{questionRows.map(q=><div key={q.id} className="card p-4"><div className="flex flex-wrap justify-between gap-2"><div><p className="font-semibold">{q.user.full_name}</p><p className="text-xs text-gray-400">{q.course_title} · {q.lesson_title}</p></div><span className="text-[11px] text-gray-400">{new Date(q.created_at).toLocaleString("fr-FR")}</span></div><p className="mt-3 text-sm text-gray-700">{q.content}</p>{q.replies?.length>0&&<div className="mt-3 space-y-2 border-l-2 border-brand-100 pl-3">{q.replies.map(r=><div key={r.id}><p className="text-xs font-semibold">{r.user.full_name}</p><p className="text-xs text-gray-600">{r.content}</p></div>)}</div>}<div className="mt-3 flex gap-2"><input value={replying===q.id?reply:""} onFocus={()=>{setReplying(q.id);setReply("");}} onChange={e=>{setReplying(q.id);setReply(e.target.value)}} placeholder="Répondre à cette question..." className="min-w-0 flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm"/><button onClick={()=>answer(q)} disabled={replying===q.id&&!reply.trim()} className="btn-primary !px-3 !py-2 !text-xs">{replying===q.id&&reply? <Send size={13}/>:<MessageSquareText size={13}/>} Répondre</button></div></div>)}{!questionRows.length&&<Empty text="Aucune question trouvée."/>}</div>}
  </div>;
}
function Empty({text}:{text:string}){return <div className="card p-8 text-center text-gray-400">{text}</div>}
