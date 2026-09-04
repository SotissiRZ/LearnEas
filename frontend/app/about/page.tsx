import Link from "next/link";
import { ArrowRight, BookOpen, BriefcaseBusiness, BadgeCheck, UsersRound } from "lucide-react";

export default function AboutPage() {
  return (
    <div>
      <section className="bg-navy-950 py-16 text-white sm:py-20">
        <div className="container-app max-w-4xl">
          <p className="kalan-eyebrow !text-brand-400">À propos de KalanPro</p>
          <h1 className="mt-3 text-4xl font-black tracking-tight sm:text-5xl">Apprendre doit mener quelque part.</h1>
          <p className="mt-6 max-w-3xl text-lg leading-8 text-white/60">KalanPro relie formation, accompagnement, pratique, certification et opportunités professionnelles dans une expérience conçue en priorité pour les usages mobiles et les réalités de l'Afrique francophone.</p>
        </div>
      </section>
      <section className="container-app py-14">
        <div className="grid gap-5 md:grid-cols-2 lg:grid-cols-4">
          <Value icon={<BookOpen />} title="Apprendre" text="Cours, cohortes live et ressources structurées." />
          <Value icon={<UsersRound />} title="Être accompagné" text="Mentorat et échanges avec des experts." />
          <Value icon={<BadgeCheck />} title="Prouver" text="Projets, portfolio et certificats vérifiables." />
          <Value icon={<BriefcaseBusiness />} title="Accéder au travail" text="Emplois, stages et missions adaptés au profil." />
        </div>
        <div className="mt-12 rounded-3xl bg-navy-50 p-7 sm:p-10">
          <h2 className="text-2xl font-black text-navy-950">Notre objectif</h2>
          <p className="mt-3 max-w-3xl leading-7 text-slate-600">Réduire la distance entre apprendre une compétence et pouvoir réellement l'utiliser dans un projet, une mission ou un emploi.</p>
          <Link href="/courses" className="btn-primary mt-6">Découvrir les formations <ArrowRight size={17} /></Link>
        </div>
      </section>
    </div>
  );
}

function Value({ icon, title, text }: { icon: React.ReactNode; title: string; text: string }) {
  return <div className="card p-5"><div className="grid h-11 w-11 place-items-center rounded-xl bg-brand-50 text-brand-600">{icon}</div><h2 className="mt-4 text-lg font-black text-navy-950">{title}</h2><p className="mt-2 text-sm leading-6 text-slate-600">{text}</p></div>;
}
