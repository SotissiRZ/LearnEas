import { notFound } from "next/navigation";
import Link from "next/link";
import {
  Clock, PlayCircle, Users, Globe, BarChart3, CheckCircle2, FileText,
} from "lucide-react";
import { api, formatDuration, formatPrice } from "@/lib/api";
import { Course } from "@/types";
import RatingStars from "@/components/ui/RatingStars";
import LevelBadge from "@/components/ui/LevelBadge";
import CourseCurriculum from "@/components/course/CourseCurriculum";
import ContactInstructorButton from "@/components/chat/ContactInstructorButton";
import CoursePurchaseCard from "@/components/course/CoursePurchaseCard";

async function getCourse(slug: string): Promise<Course | null> {
  try {
    return await api.get<Course>(`/catalog/courses/${slug}/`);
  } catch {
    return null;
  }
}

export default async function CourseDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const course = await getCourse(slug);
  if (!course) notFound();

  return (
    <div>
      {/* HEADER */}
      <section className="bg-ink text-white">
        <div className="container-app py-10 lg:py-14">
          <div className="max-w-3xl">
            {course.category && (
              <Link href={`/courses?category=${course.category.slug}`} className="text-sm font-semibold text-brand-400">
                {course.category.name}
              </Link>
            )}
            <h1 className="mt-2 text-3xl font-extrabold leading-tight sm:text-4xl">{course.title}</h1>
            <p className="mt-3 max-w-2xl text-gray-300">{course.subtitle}</p>

            <div className="mt-4 flex flex-wrap items-center gap-4 text-sm">
              <RatingStars value={parseFloat(course.rating_avg)} count={course.rating_count} />
              <span className="flex items-center gap-1 text-gray-300"><Users size={16} /> {course.students_count} étudiants</span>
              <LevelBadge level={course.level} />
            </div>

            <p className="mt-3 text-sm text-gray-300">
              Créé par <span className="font-semibold text-white">{course.instructor.full_name}</span>
              {course.instructor.headline ? ` · ${course.instructor.headline}` : ""}
            </p>

            <div className="mt-4 flex flex-wrap items-center gap-4 text-sm text-gray-300">
              <span className="flex items-center gap-1"><Globe size={16} /> {course.language}</span>
              <span className="flex items-center gap-1"><Clock size={16} /> {formatDuration(course.total_duration_minutes)} au total</span>
              <span className="flex items-center gap-1"><PlayCircle size={16} /> {course.total_lessons} vidéos</span>
              {course.pdf_resources && course.pdf_resources.length > 0 && (
                <span className="flex items-center gap-1"><FileText size={16} /> {course.pdf_resources.length} PDF inclus</span>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* PURCHASE CARD (mobile uniquement, juste sous le hero, sans chevauchement) */}
      <div className="container-app pt-6 lg:hidden">
        <CoursePurchaseCard initialCourse={course} />
      </div>

      {/* BODY */}
      <div className="container-app grid grid-cols-1 gap-10 py-10 lg:grid-cols-[1fr_380px]">
        <div className="flex flex-col gap-10">
          {course.what_you_will_learn && course.what_you_will_learn.length > 0 && (
            <section className="card p-6">
              <h2 className="mb-4 text-xl font-bold">Ce que vous allez apprendre</h2>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                {course.what_you_will_learn.map((point, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm">
                    <CheckCircle2 size={18} className="mt-0.5 shrink-0 text-brand-600" />
                    <span>{point}</span>
                  </div>
                ))}
              </div>
            </section>
          )}

          <section>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-xl font-bold">Programme du cours</h2>
              <span className="text-sm text-gray-500">
                {course.sections?.length || 0} sections · {course.total_lessons} vidéos · {formatDuration(course.total_duration_minutes)}
              </span>
            </div>
            <CourseCurriculum course={course} />
          </section>

          {course.requirements && course.requirements.length > 0 && (
            <section className="card p-6">
              <h2 className="mb-3 text-xl font-bold">Prérequis</h2>
              <ul className="list-inside list-disc space-y-1 text-sm text-gray-600">
                {course.requirements.map((r, i) => <li key={i}>{r}</li>)}
              </ul>
            </section>
          )}

          <section className="card p-6">
            <h2 className="mb-3 text-xl font-bold">Description</h2>
            <p className="whitespace-pre-line text-sm leading-relaxed text-gray-600">{course.description}</p>
          </section>

          <section className="card p-6">
            <h2 className="mb-4 flex items-center gap-2 text-xl font-bold">
              <BarChart3 size={20} /> Instructeur
            </h2>
            <div className="flex items-start gap-4">
              <div className="grid h-16 w-16 shrink-0 place-items-center rounded-full bg-brand-100 text-xl font-bold text-brand-700">
                {course.instructor.full_name[0]}
              </div>
              <div className="flex-1">
                <p className="font-bold">{course.instructor.full_name}</p>
                <p className="text-sm text-gray-500">{course.instructor.headline}</p>
                <p className="mt-2 text-sm text-gray-600">{course.instructor.bio}</p>
                <p className="mt-2 text-xs text-gray-400">
                  {course.instructor.years_experience} ans d'expérience · {course.instructor.courses_count} cours publiés
                </p>
                <ContactInstructorButton instructor={course.instructor} />
              </div>
            </div>
          </section>
        </div>

        {/* PURCHASE CARD (desktop, colonne latérale sticky · jamais sous la navbar) */}
        <div className="hidden lg:block">
          <div className="sticky top-24">
            <CoursePurchaseCard initialCourse={course} />
          </div>
        </div>
      </div>
    </div>
  );
}
