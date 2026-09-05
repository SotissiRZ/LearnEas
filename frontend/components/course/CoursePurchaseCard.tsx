"use client";

import Link from "next/link";
import { Award, Clock, FileText, PlayCircle } from "lucide-react";
import { Course } from "@/types";
import { formatDuration } from "@/lib/api";
import CurrencyPrice from "@/components/ui/CurrencyPrice";
import { useAuthenticatedResource } from "@/hooks/useAuthenticatedResource";
import { AddCourseToCartButton } from "@/components/course/AddToCartButtons";

export default function CoursePurchaseCard({ initialCourse }: { initialCourse: Course }) {
  const course = useAuthenticatedResource<Course>(`/catalog/courses/${initialCourse.slug}/`, initialCourse);

  return (
    <div className="card overflow-hidden lg:-mt-40">
      <div className="aspect-video w-full bg-gradient-to-br from-brand-100 to-brand-50">
        {course.thumbnail ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img loading="lazy" decoding="async" src={course.thumbnail} alt={course.title} className="h-full w-full object-contain bg-slate-50" />
        ) : (
          <div className="grid h-full place-items-center text-brand-300"><PlayCircle size={48} /></div>
        )}
      </div>
      <div className="p-5">
        <div className="mb-4 flex items-baseline gap-2">
          {course.discount_price ? (
            <>
              <span className="text-3xl font-extrabold"><CurrencyPrice value={course.discount_price} /></span>
              <span className="text-base text-gray-400 line-through"><CurrencyPrice value={course.price} /></span>
            </>
          ) : (
            <span className="text-3xl font-extrabold"><CurrencyPrice value={course.effective_price} /></span>
          )}
        </div>

        {course.is_enrolled ? (
          <Link href={`/learn/${course.slug}`} className="btn-primary w-full">
            <PlayCircle size={18} /> Continuer le cours
          </Link>
        ) : (
          <AddCourseToCartButton course={course} />
        )}

        <p className="mt-3 text-center text-xs text-gray-400">Accès complet à la playlist · garantie satisfait ou remboursé 14 jours</p>
        <div className="mt-5 flex flex-col gap-2 border-t border-gray-100 pt-4 text-sm text-gray-600">
          <span className="flex items-center gap-2"><PlayCircle size={16} /> {course.total_lessons} vidéos en accès illimité</span>
          <span className="flex items-center gap-2"><Clock size={16} /> {formatDuration(course.total_duration_minutes)} de contenu</span>
          {course.pdf_resources && course.pdf_resources.length > 0 && (
            <span className="flex items-center gap-2"><FileText size={16} /> {course.pdf_resources.length} ressources PDF</span>
          )}
          <span className="flex items-center gap-2"><Award size={16} /> Certificat de fin de formation</span>
        </div>
      </div>
    </div>
  );
}
