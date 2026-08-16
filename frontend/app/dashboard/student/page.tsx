"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { PlayCircle, Award, Clock, BookOpen } from "lucide-react";
import { api, formatDuration } from "@/lib/api";
import { CourseEnrollment } from "@/types";
import ProgressBar from "@/components/ui/ProgressBar";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import DashboardNav from "@/components/dashboard/DashboardNav";
import GuardScreen from "@/components/ui/GuardScreen";

export default function StudentDashboard() {
  const { ready } = useAuthGuard();
  const [enrollments, setEnrollments] = useState<CourseEnrollment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!ready) return;
    api.get<{ results: CourseEnrollment[] } | CourseEnrollment[]>("/enrollments/my-courses/")
      .then((data: any) => setEnrollments(data.results || data))
      .finally(() => setLoading(false));
  }, [ready]);

  if (!ready) return <GuardScreen />;

  const inProgress = enrollments.filter((e) => !e.completed);
  const completed = enrollments.filter((e) => e.completed);

  return (
    <div className="container-app py-10">
      <DashboardNav role="student" />

      <div className="mb-8 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Stat icon={<BookOpen size={20} />} label="Cours possédés" value={enrollments.length} />
        <Stat icon={<Clock size={20} />} label="En cours" value={inProgress.length} />
        <Stat icon={<Award size={20} />} label="Terminés" value={completed.length} />
      </div>

      <h2 className="mb-4 text-xl font-bold">Mes cours</h2>
      {loading ? (
        <p className="text-gray-500">Chargement...</p>
      ) : enrollments.length === 0 ? (
        <div className="card p-10 text-center text-gray-500">
          Vous n'avez pas encore de cours. <Link href="/courses" className="font-semibold text-brand-700">Explorer le catalogue</Link>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {enrollments.map((e) => (
            <div key={e.id} className="card overflow-hidden transition hover:-translate-y-1 hover:shadow-soft">
              <Link href={`/learn/${e.course.slug}`} className="block">
                <div className="aspect-video bg-gradient-to-br from-brand-100 to-brand-50">
                  {e.course.thumbnail && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={e.course.thumbnail} alt={e.course.title} className="h-full w-full object-cover" />
                  )}
                </div>
                <div className="p-4 pb-0">
                  <h3 className="line-clamp-2 font-bold">{e.course.title}</h3>
                  <p className="mt-1 text-xs text-gray-500">{formatDuration(e.course.total_duration_minutes)} · {e.course.total_lessons} vidéos</p>
                  <div className="mt-3">
                    <div className="mb-1 flex justify-between text-xs text-gray-500">
                      <span>{e.progress_percent}% terminé</span>
                      {e.completed && <span className="flex items-center gap-1 text-brand-700"><Award size={12} /> Certifié</span>}
                    </div>
                    <ProgressBar value={e.progress_percent} />
                  </div>
                </div>
              </Link>
              <div className="p-4 pt-4">
                <Link href={`/learn/${e.course.slug}`} className="btn-primary w-full !py-2 !text-sm">
                  <PlayCircle size={16} /> {e.progress_percent > 0 ? "Continuer" : "Commencer"}
                </Link>
                {e.certificate_issued && (
                  <Link
                    href={`/certificate/${e.id}`}
                    className="btn-outline mt-2 w-full !py-2 !text-sm !border-amber-400 !text-amber-700"
                  >
                    <Award size={16} /> Voir le certificat
                  </Link>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Stat({ icon, label, value }: { icon: React.ReactNode; label: string; value: number }) {
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
