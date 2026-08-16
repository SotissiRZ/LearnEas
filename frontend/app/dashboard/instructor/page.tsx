"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { BookOpen, FileText, Users, Star, PlusCircle } from "lucide-react";
import { api } from "@/lib/api";
import { Course, PDFProduct } from "@/types";
import { useAuth } from "@/hooks/useAuth";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import DashboardNav from "@/components/dashboard/DashboardNav";
import GuardScreen from "@/components/ui/GuardScreen";

export default function InstructorDashboard() {
  const { ready } = useAuthGuard(); // connexion requise, tous rôles acceptés (un étudiant peut devenir instructeur)
  const { user } = useAuth();
  const [courses, setCourses] = useState<Course[]>([]);
  const [pdfs, setPdfs] = useState<PDFProduct[]>([]);

  useEffect(() => {
    if (!ready || !user) return;
    api.get<{ results: Course[] } | Course[]>("/catalog/courses/my_courses/")
      .then((d: any) => setCourses(d.results || d)).catch(() => {});
    api.get<{ results: PDFProduct[] } | PDFProduct[]>("/catalog/pdfs/my_pdfs/")
      .then((d: any) => setPdfs(d.results || d)).catch(() => {});
  }, [ready, user]);

  if (!ready) return <GuardScreen />;

  if (user && user.role !== "instructor" && user.role !== "admin") {
    return <BecomeInstructor />;
  }

  const totalStudents = courses.reduce((sum, c) => sum + c.students_count, 0);
  const avgRating = courses.length
    ? (courses.reduce((sum, c) => sum + parseFloat(c.rating_avg), 0) / courses.length).toFixed(1)
    : "0.0";

  return (
    <div className="container-app py-10">
      <DashboardNav role="instructor" />

      <div className="mb-8 grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Stat icon={<BookOpen size={20} />} label="Cours publiés" value={courses.length} />
        <Stat icon={<FileText size={20} />} label="PDF publiés" value={pdfs.length} />
        <Stat icon={<Users size={20} />} label="Étudiants" value={totalStudents} />
        <Stat icon={<Star size={20} />} label="Note moyenne" value={avgRating} />
      </div>

      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-bold">Mes cours récents</h2>
        <Link href="/dashboard/instructor/courses/new" className="btn-primary !py-2 !text-sm">
          <PlusCircle size={16} /> Nouveau cours
        </Link>
      </div>
      {courses.length === 0 ? (
        <p className="mb-8 text-gray-500">Aucun cours publié pour le moment.</p>
      ) : (
        <div className="mb-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {courses.slice(0, 6).map((c) => (
            <Link key={c.id} href={`/dashboard/instructor/courses/${c.id}`} className="card p-4 transition hover:-translate-y-1 hover:shadow-soft">
              <p className="line-clamp-2 font-semibold">{c.title}</p>
              <p className="mt-1 text-xs text-gray-500">{c.total_lessons} vidéos · {c.students_count} étudiants</p>
              <span className={`badge mt-2 ${c.published ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-600"}`}>
                {c.published ? "Publié" : "Brouillon"}
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: number | string }) {
  return (
    <div className="card flex items-center gap-3 p-4">
      <div className="grid h-11 w-11 place-items-center rounded-xl bg-brand-50 text-brand-600">{icon}</div>
      <div>
        <p className="text-xl font-extrabold">{value}</p>
        <p className="text-xs text-gray-500">{label}</p>
      </div>
    </div>
  );
}

function BecomeInstructor() {
  const { refreshMe } = useAuth();
  const [form, setForm] = useState({ domain: "", years_experience: "0", headline: "" });
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post("/auth/become-instructor/", form);
      await refreshMe();
      window.location.reload();
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container-app flex min-h-[60vh] items-center justify-center py-16">
      <form onSubmit={handleSubmit} className="card w-full max-w-md p-8">
        <h1 className="mb-1 text-2xl font-extrabold">Devenir instructeur</h1>
        <p className="mb-6 text-sm text-gray-500">Publiez vos cours et PDF sur LearnEas.</p>
        <div className="flex flex-col gap-4">
          <input required placeholder="Domaine d'expertise (ex: Développement web)"
            value={form.domain} onChange={(e) => setForm({ ...form, domain: e.target.value })}
            className="rounded-lg border border-gray-200 px-3 py-2 text-sm" />
          <input required type="number" placeholder="Années d'expérience"
            value={form.years_experience} onChange={(e) => setForm({ ...form, years_experience: e.target.value })}
            className="rounded-lg border border-gray-200 px-3 py-2 text-sm" />
          <input placeholder="Titre professionnel (ex: Expert Django)"
            value={form.headline} onChange={(e) => setForm({ ...form, headline: e.target.value })}
            className="rounded-lg border border-gray-200 px-3 py-2 text-sm" />
          <button type="submit" disabled={loading} className="btn-primary">
            {loading ? "Envoi..." : "Devenir instructeur"}
          </button>
        </div>
      </form>
    </div>
  );
}
