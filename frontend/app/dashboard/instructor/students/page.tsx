"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { Search, Users, MessageCircle, BookOpen, FileText, Video } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import GuardScreen from "@/components/ui/GuardScreen";

interface StudentRow {
  id: string; user_id: number; name: string; email: string; content_type: "course" | "pdf" | "formation";
  content_id: number; content_title: string; progress_percent: number | null; completed: boolean; acquired_at: string;
}

export default function InstructorStudentsPage() {
  const { ready } = useAuthGuard({ roles: ["instructor", "admin"], redirectTo: "/dashboard/instructor" });
  const [rows, setRows] = useState<StudentRow[]>([]);
  const [uniqueStudents, setUniqueStudents] = useState(0);
  const [search, setSearch] = useState("");
  const [type, setType] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!ready) return;
    api.get<{ results: StudentRow[]; unique_students: number }>("/auth/instructor/students/")
      .then((d) => { setRows(d.results); setUniqueStudents(d.unique_students); })
      .catch((e) => setError(e instanceof ApiError ? e.message : "Impossible de charger les étudiants."))
      .finally(() => setLoading(false));
  }, [ready]);

  const filtered = useMemo(() => rows.filter((r) => {
    const q = search.trim().toLowerCase();
    return (type === "all" || r.content_type === type) && (!q || `${r.name} ${r.email} ${r.content_title}`.toLowerCase().includes(q));
  }), [rows, search, type]);

  if (!ready) return <GuardScreen />;
  return <div className="min-w-0">
    <div className="mb-6"><h1 className="text-xl font-bold">Étudiants</h1><p className="mt-1 text-sm text-gray-500">{uniqueStudents} apprenant(s) unique(s) sur l'ensemble de vos contenus.</p></div>
    <div className="card mb-4 flex flex-wrap gap-3 p-4">
      <div className="relative min-w-[220px] flex-1"><Search size={15} className="absolute left-3 top-2.5 text-gray-400" /><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Rechercher un étudiant ou un contenu" className="w-full rounded-lg border border-gray-200 py-2 pl-9 pr-3 text-sm" /></div>
      <select value={type} onChange={(e) => setType(e.target.value)} className="rounded-lg border border-gray-200 px-3 py-2 text-sm"><option value="all">Tous les accès</option><option value="course">Cours</option><option value="formation">Formations live</option><option value="pdf">PDF</option></select>
    </div>
    {error && <div className="mb-4 rounded-xl bg-red-50 p-3 text-sm text-red-700">{error}</div>}
    {loading ? <div className="card p-8 text-center text-gray-500">Chargement...</div> : <div className="card overflow-hidden">
      <div className="max-h-[620px] overflow-auto"><table className="w-full min-w-[760px] text-sm"><thead className="sticky top-0 bg-gray-50 text-left text-xs text-gray-500"><tr><th className="px-4 py-3">Étudiant</th><th className="px-4 py-3">Accès</th><th className="px-4 py-3">Contenu</th><th className="px-4 py-3">Progression</th><th className="px-4 py-3">Date</th><th className="px-4 py-3">Action</th></tr></thead><tbody className="divide-y divide-gray-100">{filtered.map((r) => <tr key={r.id}><td className="px-4 py-3"><p className="font-semibold">{r.name}</p><p className="text-xs text-gray-400">{r.email}</p></td><td className="px-4 py-3"><TypeBadge type={r.content_type} /></td><td className="px-4 py-3 font-medium">{r.content_title}</td><td className="px-4 py-3">{r.progress_percent == null ? <span className="text-gray-400">—</span> : <div className="w-28"><div className="mb-1 flex justify-between text-[10px] text-gray-400"><span>{r.progress_percent}%</span><span>{r.completed ? "Terminé" : "En cours"}</span></div><div className="h-1.5 overflow-hidden rounded-full bg-gray-100"><div className="h-full bg-brand-600" style={{ width: `${r.progress_percent}%` }} /></div></div>}</td><td className="px-4 py-3 text-xs text-gray-500">{new Date(r.acquired_at).toLocaleDateString("fr-FR")}</td><td className="px-4 py-3"><Link href={`/dashboard/instructor/messages?with=${r.user_id}`} className="inline-flex items-center gap-1 text-xs font-semibold text-brand-700"><MessageCircle size={13} /> Message</Link></td></tr>)}{filtered.length === 0 && <tr><td colSpan={6} className="px-4 py-10 text-center text-gray-400"><Users className="mx-auto mb-2" size={24} />Aucun résultat.</td></tr>}</tbody></table></div>
    </div>}
  </div>;
}
function TypeBadge({ type }: { type: StudentRow["content_type"] }) { const map = { course: [BookOpen, "Cours"], pdf: [FileText, "PDF"], formation: [Video, "Live"] } as const; const [Icon, label] = map[type]; return <span className="badge bg-gray-100 text-gray-700"><Icon size={11} className="mr-1 inline" />{label}</span>; }
