import { safePublicGet } from "@/lib/serverPublicApi";
import { Course, Paginated } from "@/types";
import { Users, BookOpen, BriefcaseBusiness, Sparkles } from "lucide-react";
import ContactInstructorButton from "@/components/chat/ContactInstructorButton";

export default async function InstructorsPage() {
  const result = await safePublicGet<Paginated<Course>>("/catalog/courses/?ordering=-students_count", {
    count: 0,
    next: null,
    previous: null,
    results: [],
  }, 60);
  const data = result.data;

  const instructorsMap = new Map<
    number,
    { instructor: Course["instructor"]; courses: number; students: number }
  >();

  data.results.forEach((course) => {
    const existing = instructorsMap.get(course.instructor.id);
    if (existing) {
      existing.courses += 1;
      existing.students += course.students_count;
    } else {
      instructorsMap.set(course.instructor.id, {
        instructor: course.instructor,
        courses: 1,
        students: course.students_count,
      });
    }
  });

  const instructors = Array.from(instructorsMap.values());

  return (
    <div className="container-app py-10">
      <div className="mb-8 flex flex-col gap-2">
        <span className="text-sm font-semibold uppercase tracking-wide text-brand-700">
          Réseau d'experts
        </span>
        <h1 className="text-3xl font-extrabold text-ink sm:text-4xl">Nos instructeurs</h1>
        <p className="max-w-3xl text-sm text-gray-500 sm:text-base">
          Découvrez les formateurs KalanPro, leurs expertises et les cours qu&apos;ils animent.
          Chaque carte met en avant le domaine, l&apos;expérience et l&apos;activité pédagogique.
        </p>
      </div>

      {instructors.length === 0 ? (
        <p className="text-gray-500">Aucun instructeur pour le moment.</p>
      ) : (
        <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
          {instructors.map(({ instructor, courses, students }) => {
            const firstName = instructor.full_name.split(" ")[0] || instructor.full_name;
            return (
              <article
                key={instructor.id}
                className="card flex h-full min-h-[270px] flex-col p-5 transition hover:-translate-y-0.5 hover:border-brand-100 hover:shadow-soft"
              >
                <div className="flex items-start gap-4">
                  <div className="grid h-16 w-16 shrink-0 place-items-center rounded-full bg-brand-100 text-2xl font-extrabold text-brand-700">
                    {instructor.full_name[0]}
                  </div>
                  <div className="min-w-0 flex-1">
                    <h2 className="text-xl font-bold leading-tight text-ink">{instructor.full_name}</h2>
                    <p className="mt-1 text-base text-gray-600">{instructor.headline}</p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      <span className="inline-flex items-center gap-1 rounded-full bg-brand-50 px-3 py-1 text-xs font-medium text-brand-700">
                        <Sparkles size={12} /> {instructor.domain}
                      </span>
                      <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600">
                        <BriefcaseBusiness size={12} /> {instructor.years_experience} ans d&apos;expérience
                      </span>
                    </div>
                  </div>
                </div>

                <div className="mt-5 space-y-3">
                  <div className="rounded-2xl bg-gray-50 p-4">
                    <p className="line-clamp-2 text-sm leading-6 text-gray-600">
                      {instructor.bio?.trim()
                        ? instructor.bio
                        : `${instructor.headline || "Expert KalanPro"} spécialisé(e) en ${instructor.domain.toLowerCase()}.`}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="rounded-2xl border border-gray-100 bg-white p-3">
                      <div className="flex items-center gap-2 text-brand-700">
                        <BookOpen size={15} />
                        <span className="text-[11px] font-semibold uppercase tracking-wide">Cours</span>
                      </div>
                      <p className="mt-1.5 text-xl font-bold text-ink">{courses}</p>
                    </div>
                    <div className="rounded-2xl border border-gray-100 bg-white p-3">
                      <div className="flex items-center gap-2 text-brand-700">
                        <Users size={15} />
                        <span className="text-[11px] font-semibold uppercase tracking-wide">Étudiants</span>
                      </div>
                      <p className="mt-1.5 text-xl font-bold text-ink">{students}</p>
                    </div>
                  </div>
                </div>

                <div className="mt-auto flex justify-end pt-4">
                  <ContactInstructorButton
                    instructor={instructor}
                    buttonLabel={`Contacter ${firstName}`}
                    className="inline-flex items-center justify-center gap-2 rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-700 shadow-soft"
                  />
                </div>
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}
