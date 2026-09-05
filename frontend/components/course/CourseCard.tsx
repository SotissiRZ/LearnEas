import Link from "next/link";
import { Clock, PlayCircle, Users } from "lucide-react";
import { Course } from "@/types";
import { formatDuration } from "@/lib/api";
import CurrencyPrice from "@/components/ui/CurrencyPrice";
import RatingStars from "@/components/ui/RatingStars";
import LevelBadge from "@/components/ui/LevelBadge";
import QuickAddButton from "@/components/course/QuickAddButton";

export default function CourseCard({ course }: { course: Course }) {
  return (
    <Link
      href={`/courses/${course.slug}`}
      className="card catalog-card group flex flex-col overflow-hidden transition hover:-translate-y-1 hover:shadow-soft"
    >
      <div className="relative aspect-[16/10] w-full overflow-hidden bg-gradient-to-br from-brand-100 to-brand-50">
        {course.thumbnail ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img loading="lazy" decoding="async" src={course.thumbnail} alt={course.title} className="h-full w-full object-cover object-center transition duration-300 group-hover:scale-[1.02]" />
        ) : (
          <div className="grid h-full place-items-center text-brand-300">
            <PlayCircle size={48} />
          </div>
        )}
        {course.is_free && (
          <span className="badge absolute left-3 top-3 bg-white/95 text-brand-700 shadow">Gratuit</span>
        )}
        {course.discount_price && (
          <span className="badge absolute right-3 top-3 bg-rose-600 text-white">Promo</span>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-1.5 p-3.5 sm:p-4">
        <div className="flex items-center gap-2">
          <LevelBadge level={course.level} />
          {course.category && (
            <span className="text-xs font-medium text-gray-400">{course.category.name}</span>
          )}
        </div>

        <h3 className="line-clamp-2 text-base font-bold leading-snug text-ink group-hover:text-brand-700">
          {course.title}
        </h3>
        <p className="line-clamp-2 text-sm text-gray-500">{course.subtitle}</p>

        <p className="text-xs font-medium text-gray-500">{course.instructor?.full_name}</p>

        <RatingStars value={parseFloat(course.rating_avg)} count={course.rating_count} />

        <div className="mt-1 flex items-center gap-3 text-xs text-gray-500">
          <span className="flex items-center gap-1"><Clock size={14} /> {formatDuration(course.total_duration_minutes)}</span>
          <span className="flex items-center gap-1"><PlayCircle size={14} /> {course.total_lessons} vidéos</span>
          <span className="flex items-center gap-1"><Users size={14} /> {course.students_count}</span>
        </div>

        <div className="mt-auto flex items-center justify-between gap-2 pt-2">
          <div className="flex items-center gap-2">
            {course.discount_price ? (
              <>
                <span className="text-lg font-extrabold text-ink"><CurrencyPrice value={course.discount_price} /></span>
                <span className="text-sm text-gray-400 line-through"><CurrencyPrice value={course.price} /></span>
              </>
            ) : (
              <span className="text-lg font-extrabold text-ink"><CurrencyPrice value={course.effective_price} /></span>
            )}
          </div>
          <QuickAddButton item={{ kind: "course", data: course }} />
        </div>
      </div>
    </Link>
  );
}
