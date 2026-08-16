"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PlusCircle, Users, PlayCircle, Pencil } from "lucide-react";
import { api, formatDuration } from "@/lib/api";
import { Course } from "@/types";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import DashboardNav from "@/components/dashboard/DashboardNav";
import GuardScreen from "@/components/ui/GuardScreen";

export default function InstructorCoursesPage() {
  const { ready } = useAuthGuard({ roles: ["instructor", "admin"], redirectTo: "/dashboard/instructor" });
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ready) return;
    api.get<{ results: Course[] } | Course[]>("/catalog/courses/my_courses/")
      .then((d: any) => setCourses(d.results || d))
      .finally(() => setLoading(false));
  }, [ready]);

  if (!ready) return <GuardScreen />;

  return (
    <div className="container-app py-10">
      <DashboardNav role="instructor" />
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-bold">Mes cours</h1>
        <Link href="/dashboard/instructor/courses/new" className="btn-primary !py-2 !text-sm">
          <PlusCircle size={16} /> Nouveau cours
        </Link>
      </div>

      {loading ? (
        <p className="text-gray-500">Chargement...</p>
      ) : courses.length === 0 ? (
        <div className="card p-10 text-center text-gray-500">Vous n'avez pas encore créé de cours.</div>
      ) : (
        <div className="flex flex-col gap-3">
          {courses.map((c) => (
            <div key={c.id} className="card flex items-center gap-4 p-4">
              <div className="flex h-16 w-24 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-gray-100">
                {c.thumbnail ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={c.thumbnail} alt={c.title} className="h-full w-full object-cover" />
                ) : <PlayCircle className="text-gray-300" />}
              </div>
              <div className="flex-1">
                <p className="font-semibold">{c.title}</p>
                <p className="text-xs text-gray-500">
                  {c.total_lessons} vidéos · {formatDuration(c.total_duration_minutes)} · <Users size={12} className="inline" /> {c.students_count}
                </p>
              </div>
              <span className={`badge ${c.published ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-600"}`}>
                {c.published ? "Publié" : "Brouillon"}
              </span>
              <Link href={`/dashboard/instructor/courses/${c.id}`} className="btn-outline !py-1.5 !text-xs">
                <Pencil size={14} /> Gérer
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
