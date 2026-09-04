import { notFound } from "next/navigation";
import { Clock3, GraduationCap, Languages, ShieldCheck } from "lucide-react";
import { api } from "@/lib/api";
import { MentorshipOffering } from "@/types";
import MentorshipBookingCard from "@/components/mentorship/MentorshipBookingCard";

async function getOffer(slug: string): Promise<MentorshipOffering | null> {
  try { return await api.get<MentorshipOffering>(`/mentorship/offerings/${slug}/`); } catch { return null; }
}

export default async function MentorshipDetailPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const offer = await getOffer(slug);
  if (!offer) notFound();
  return <div className="container-app grid gap-8 py-10 lg:grid-cols-[1fr_380px]">
    <main className="min-w-0 space-y-6">
      <div>
        <span className="badge bg-brand-50 text-brand-700">Mentorat individuel</span>
        <h1 className="mt-3 text-3xl font-extrabold">{offer.title}</h1>
        <div className="mt-4 flex flex-wrap gap-4 text-sm text-gray-500"><span className="flex items-center gap-1"><Clock3 size={16}/>{offer.duration_minutes} minutes</span><span className="flex items-center gap-1"><Languages size={16}/>{offer.language}</span><span className="flex items-center gap-1"><ShieldCheck size={16}/>Salle privée KalanPro</span></div>
      </div>
      <section className="card p-6"><h2 className="text-lg font-bold">À propos de cette séance</h2><p className="mt-3 whitespace-pre-line text-sm leading-7 text-gray-600">{offer.description}</p></section>
      <section className="card p-6"><div className="flex items-start gap-4">{offer.instructor.avatar ? <img src={offer.instructor.avatar} alt="" loading="lazy" decoding="async" className="h-16 w-16 rounded-full object-cover"/> : <span className="grid h-16 w-16 place-items-center rounded-full bg-brand-50 text-brand-700"><GraduationCap size={28}/></span>}<div><h2 className="font-bold">{offer.instructor.full_name}</h2><p className="text-sm text-brand-700">{offer.instructor.headline || offer.instructor.domain || "Instructeur KalanPro"}</p><p className="mt-2 text-sm leading-6 text-gray-500">{offer.instructor.bio || "Mentor vérifié sur KalanPro."}</p></div></div></section>
      <section className="rounded-2xl border border-blue-100 bg-blue-50 p-5 text-sm leading-6 text-blue-900"><strong>Comment ça marche ?</strong> Choisissez un créneau, finalisez le paiement si nécessaire, puis retrouvez votre rendez-vous dans votre espace apprenant. La salle de visioconférence KalanPro devient accessible au moment de la séance.</section>
    </main>
    <MentorshipBookingCard offering={offer}/>
  </div>;
}
