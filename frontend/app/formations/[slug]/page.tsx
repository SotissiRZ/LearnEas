import { notFound } from "next/navigation";
import { Users } from "lucide-react";
import { api } from "@/lib/api";
import { InteractiveFormation } from "@/types";
import LevelBadge from "@/components/ui/LevelBadge";
import ContactInstructorButton from "@/components/chat/ContactInstructorButton";
import FormationSchedule from "@/components/formation/FormationSchedule";
import FormationAccessCard from "@/components/formation/FormationAccessCard";

async function getFormation(slug: string): Promise<InteractiveFormation | null> {
  try {
    return await api.get<InteractiveFormation>(`/formations/${slug}/`);
  } catch {
    return null;
  }
}

export default async function FormationDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const formation = await getFormation(slug);
  if (!formation) notFound();

  return (
    <div className="container-app grid grid-cols-1 gap-10 py-10 lg:grid-cols-[1fr_380px]">
      <div className="flex flex-col gap-8">
        <div>
          <span className="badge bg-violet-50 text-violet-700">Formation interactive en direct</span>
          <h1 className="mt-2 text-3xl font-extrabold">{formation.title}</h1>
          <div className="mt-3 flex flex-wrap items-center gap-4 text-sm">
            <LevelBadge level={formation.level} />
            <span className="flex items-center gap-1 text-gray-500"><Users size={16} /> {formation.students_count} inscrit(s) · {formation.seats_left} places restantes</span>
          </div>
          <p className="mt-2 text-sm text-gray-500">
            Animée par <span className="font-semibold">{formation.instructor.full_name}</span>
            {formation.co_instructor && <> et <span className="font-semibold">{formation.co_instructor.full_name}</span></>}
          </p>
          <ContactInstructorButton instructor={formation.instructor} />
        </div>

        <div className="card p-6">
          <h2 className="mb-3 text-xl font-bold">Description</h2>
          <p className="whitespace-pre-line text-sm leading-relaxed text-gray-600">{formation.description}</p>
        </div>

        <div className="card p-6">
          <h2 className="mb-4 text-xl font-bold">Planning des séances</h2>
          <FormationSchedule initialFormation={formation} />
        </div>
      </div>

      <div>
        <FormationAccessCard initialFormation={formation} />
      </div>
    </div>
  );
}
