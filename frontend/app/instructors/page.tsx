import { api } from "@/lib/api";
import { Course, Paginated } from "@/types";
import { Star, Users, BookOpen } from "lucide-react";
import ContactInstructorButton from "@/components/chat/ContactInstructorButton";

async function safeGet<T>(path: string, fallback: T): Promise<T> {
  try { return await api.get<T>(path); } catch { return fallback; }
}

export default async function InstructorsPage() {
  const data = await safeGet<Paginated<Course>>("/catalog/courses/?ordering=-students_count", {
    count: 0, next: null, previous: null, results: [],
  });

  const instructorsMap = new Map<number, { instructor: Course["instructor"]; courses: number; students: number }>();
  data.results.forEach((c) => {
    const existing = instructorsMap.get(c.instructor.id);
    if (existing) {
      existing.courses += 1;
      existing.students += c.students_count;
    } else {
      instructorsMap.set(c.instructor.id, { instructor: c.instructor, courses: 1, students: c.students_count });
    }
  });
  const instructors = Array.from(instructorsMap.values());

  return (
    <div className="container-app py-10">
      <h1 className="mb-6 text-3xl font-extrabold">Nos instructeurs</h1>
      {instructors.length === 0 ? (
        <p className="text-gray-500">Aucun instructeur pour le moment.</p>
      ) : (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {instructors.map(({ instructor, courses, students }) => (
            <div key={instructor.id} className="card p-6">
              <div className="mb-3 grid h-16 w-16 place-items-center rounded-full bg-brand-100 text-xl font-bold text-brand-700">
                {instructor.full_name[0]}
              </div>
              <p className="font-bold">{instructor.full_name}</p>
              <p className="text-sm text-gray-500">{instructor.headline}</p>
              <p className="mt-2 text-xs text-gray-500">{instructor.domain} · {instructor.years_experience} ans d'expérience</p>
              <div className="mt-4 flex gap-4 text-xs text-gray-500">
                <span className="flex items-center gap-1"><BookOpen size={14} /> {courses} cours</span>
                <span className="flex items-center gap-1"><Users size={14} /> {students} étudiants</span>
              </div>
              <ContactInstructorButton instructor={instructor} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
