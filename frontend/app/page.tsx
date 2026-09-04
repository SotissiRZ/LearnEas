import Link from "next/link";
import Image from "next/image";
import {
  ArrowRight, BookOpen, BriefcaseBusiness, UsersRound, Search, Rocket,
  BadgeCheck, Wifi, Smartphone, Sparkles,
} from "lucide-react";
import { safePublicGet } from "@/lib/serverPublicApi";
import { Course, Domain, PDFProduct } from "@/types";
import CourseCard from "@/components/course/CourseCard";
import PdfCard from "@/components/pdf/PdfCard";
import CategoryIcon from "@/components/ui/CategoryIcon";
import ApiErrorBanner from "@/components/ui/ApiErrorBanner";

export default async function HomePage() {
  const [domainsResult, featuredResult, pdfsResult] = await Promise.all([
    safePublicGet<Domain[]>("/catalog/domains/", [], 300),
    safePublicGet<Course[]>("/catalog/courses/featured/", [], 60),
    safePublicGet<{ results: PDFProduct[] }>("/catalog/pdfs/?ordering=-created_at", { results: [] }, 60),
  ]);
  const domains = domainsResult.data;
  const featuredCourses = featuredResult.data;
  const pdfs = pdfsResult.data;
  const hasError = !domainsResult.ok || !featuredResult.ok || !pdfsResult.ok;

  return (
    <div className="bg-white">
      {hasError && <div className="container-app pt-5"><ApiErrorBanner message={domainsResult.error || featuredResult.error || pdfsResult.error} /></div>}

      <section className="relative overflow-hidden bg-navy-950 text-white">
        <div className="absolute inset-0 bg-hero-radial" />
        <div className="container-app relative z-10 grid min-h-[590px] items-center gap-9 py-12 lg:grid-cols-[1.02fr_.98fr] lg:gap-12 lg:py-16">
          <div className="max-w-2xl">
            <span className="mb-5 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs font-bold text-white/75">
              <Sparkles size={14} className="text-brand-400" /> Pensé pour l'Afrique francophone
            </span>
            <h1 className="text-4xl font-black leading-[1.08] tracking-tight sm:text-5xl lg:text-6xl">
              Apprenez. Évoluez.<br />
              <span className="text-brand-500">Trouvez un emploi.</span>
            </h1>
            <p className="mt-6 max-w-xl text-base leading-7 text-white/70 sm:text-lg">
              La plateforme francophone de formation, mentorat et opportunités professionnelles qui vous connecte aux compétences, aux experts et aux bonnes opportunités.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link href="/courses" className="btn-primary !px-6 !py-3.5 !text-base"><BookOpen size={19} /> Découvrir les cours</Link>
              <Link href="/opportunities" className="btn-dark !px-6 !py-3.5 !text-base"><Search size={18} /> Trouver un emploi</Link>
            </div>
            <div className="mt-8 flex flex-wrap gap-x-5 gap-y-2 text-xs font-semibold text-white/60">
              <span className="flex items-center gap-1.5"><Smartphone size={14} className="text-brand-400" /> Mobile-first</span>
              <span className="flex items-center gap-1.5"><Wifi size={14} className="text-brand-400" /> Faible connexion</span>
              <span className="flex items-center gap-1.5"><BadgeCheck size={14} className="text-brand-400" /> Certificats vérifiables</span>
            </div>
          </div>

          <div className="relative min-h-[300px] overflow-hidden rounded-[26px] border border-white/10 bg-navy-900 shadow-[0_24px_70px_rgba(0,0,0,.28)] sm:min-h-[390px] lg:min-h-[500px] lg:rounded-[34px]">
            <Image
              src="/images/hero-kalanpro.webp"
              alt="Apprenants KalanPro collaborant autour de leurs ordinateurs"
              fill
              priority
              sizes="(max-width: 1024px) 100vw, 46vw"
              className="object-cover object-center"
            />
            <div className="absolute inset-0 bg-gradient-to-r from-navy-950/25 via-transparent to-transparent" />
            <div className="absolute inset-x-0 bottom-0 h-28 bg-gradient-to-t from-navy-950/70 to-transparent" />
            <div className="absolute bottom-5 left-5 right-5 flex flex-wrap gap-2 text-[11px] font-bold text-white/90 sm:text-xs">
              <span className="rounded-full border border-white/15 bg-navy-950/65 px-3 py-1.5 backdrop-blur">Formation</span>
              <span className="rounded-full border border-white/15 bg-navy-950/65 px-3 py-1.5 backdrop-blur">Mentorat</span>
              <span className="rounded-full border border-white/15 bg-navy-950/65 px-3 py-1.5 backdrop-blur">Emploi</span>
            </div>
          </div>
        </div>

        <div className="container-app relative z-20 pb-8 lg:-mt-3">
          <div className="grid gap-4 md:grid-cols-3">
            <FeatureCard
              icon={<BookOpen size={24} />}
              iconClass="bg-blue-600/20 text-blue-300"
              title="Formations en ligne"
              text="Développez vos compétences avec des cours interactifs, des cohortes live et des ressources adaptées au mobile."
              href="/courses"
              link="Voir les formations"
              accent="text-blue-300"
            />
            <FeatureCard
              icon={<UsersRound size={25} />}
              iconClass="bg-brand-500/20 text-brand-400"
              title="Mentorat personnalisé"
              text="Trouvez le mentor idéal pour vous guider, partager son expérience et accélérer votre progression."
              href="/mentorship"
              link="Rencontrer un mentor"
              accent="text-brand-400"
            />
            <FeatureCard
              icon={<BriefcaseBusiness size={24} />}
              iconClass="bg-emerald-500/20 text-emerald-300"
              title="Opportunités de carrière"
              text="Accédez à des emplois, stages et missions adaptés à votre profil, vos compétences et votre portfolio."
              href="/opportunities"
              link="Chercher un emploi"
              accent="text-emerald-300"
            />
          </div>
        </div>
      </section>

      <section className="bg-slate-50 py-14">
        <div className="container-app">
          <div className="mb-7 max-w-2xl">
            <p className="kalan-eyebrow">Un parcours complet</p>
            <h2 className="kalan-section-title mt-2">De la compétence à l'opportunité</h2>
            <p className="mt-3 text-sm leading-6 text-slate-600 sm:text-base">KalanPro rassemble apprentissage, pratique, mentorat, preuve de compétence et mise en relation professionnelle dans un même parcours.</p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["01", "Apprendre", "Cours, PDF et cohortes live pensés pour une consommation mobile."],
              ["02", "Pratiquer", "Projets concrets, remises, corrections et portfolio vérifié."],
              ["03", "Être accompagné", "Mentorat individuel et suivi avec des experts du terrain."],
              ["04", "Travailler", "Matching avec des emplois, stages et missions selon votre profil."],
            ].map(([num, title, text]) => (
              <div key={num} className="card p-5">
                <span className="text-sm font-black text-brand-500">{num}</span>
                <h3 className="mt-3 text-lg font-black text-navy-950">{title}</h3>
                <p className="mt-2 text-sm leading-6 text-slate-600">{text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {domains.length > 0 && (
        <section className="container-app py-14">
          <div className="mb-7 flex flex-col justify-between gap-3 sm:flex-row sm:items-end">
            <div><p className="kalan-eyebrow">Explorer</p><h2 className="kalan-section-title mt-2">Choisir un domaine</h2></div>
            <Link href="/courses" className="flex items-center gap-1 text-sm font-bold text-brand-600">Toutes les formations <ArrowRight size={16} /></Link>
          </div>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
            {domains.filter((domain) => domain.slug !== "autres-domaines").map((domain) => (
              <Link key={domain.id} href={`/courses?domain=${domain.slug}`} className="card group flex flex-col items-center gap-2 p-5 text-center transition hover:-translate-y-1 hover:border-brand-200 hover:shadow-soft">
                <div className="grid h-11 w-11 place-items-center rounded-xl bg-brand-50 text-brand-600 transition group-hover:bg-brand-500 group-hover:text-white"><CategoryIcon name={domain.icon} size={22} /></div>
                <span className="text-sm font-bold text-navy-950">{domain.name}</span>
                <span className="text-xs text-slate-400">{domain.courses_count || 0} cours</span>
              </Link>
            ))}
          </div>
        </section>
      )}

      <section className="bg-navy-50/60 py-14">
        <div className="container-app">
          <div className="mb-7 flex items-end justify-between gap-3">
            <div><p className="kalan-eyebrow">Sélection</p><h2 className="kalan-section-title mt-2">Formations à la une</h2></div>
            <Link href="/courses" className="flex items-center gap-1 text-sm font-bold text-brand-600">Voir tout <ArrowRight size={16} /></Link>
          </div>
          {featuredCourses.length === 0 ? <p className="text-slate-500">Aucun cours disponible pour le moment.</p> : (
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">{featuredCourses.map((c) => <CourseCard key={c.id} course={c} />)}</div>
          )}
        </div>
      </section>

      <section className="container-app py-14">
        <div className="mb-7 flex items-end justify-between gap-3">
          <div><p className="kalan-eyebrow">Ressources</p><h2 className="kalan-section-title mt-2">PDF & Guides populaires</h2></div>
          <Link href="/pdfs" className="flex items-center gap-1 text-sm font-bold text-brand-600">Voir tout <ArrowRight size={16} /></Link>
        </div>
        {pdfs.results.length === 0 ? <p className="text-slate-500">Aucun PDF disponible pour le moment.</p> : (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">{pdfs.results.slice(0, 8).map((p) => <PdfCard key={p.id} pdf={p} />)}</div>
        )}
      </section>

      <section className="container-app pb-16">
        <div className="relative overflow-hidden rounded-[28px] bg-navy-950 px-6 py-8 text-white shadow-soft sm:px-9 lg:flex lg:items-center lg:justify-between lg:px-12 lg:py-10">
          <div className="absolute -bottom-24 -right-16 h-64 w-64 rounded-full bg-brand-500/30 blur-3xl" />
          <div className="relative flex items-start gap-4">
            <span className="grid h-14 w-14 shrink-0 place-items-center rounded-2xl border border-white/10 bg-white/5 text-brand-400"><Rocket size={28} /></span>
            <div><h2 className="text-2xl font-black sm:text-3xl">Prêt à franchir la prochaine étape ?</h2><p className="mt-2 text-sm text-white/60 sm:text-base">Inscrivez-vous dès aujourd'hui et construisez votre prochain niveau avec KalanPro.</p></div>
          </div>
          <div className="relative mt-6 flex flex-col gap-3 sm:flex-row lg:mt-0 lg:pl-8">
            <Link href="/register" className="btn-primary !px-6 !py-3.5">S'inscrire maintenant <ArrowRight size={17} /></Link>
            <Link href="/about" className="btn-dark !px-6 !py-3.5">En savoir plus <ArrowRight size={17} /></Link>
          </div>
        </div>
      </section>
    </div>
  );
}

function FeatureCard({ icon, iconClass, title, text, href, link, accent }: { icon: React.ReactNode; iconClass: string; title: string; text: string; href: string; link: string; accent: string }) {
  return (
    <article className="rounded-2xl border border-white/10 bg-navy-900/80 p-5 shadow-[0_18px_45px_rgba(0,0,0,.18)] backdrop-blur">
      <div className={`grid h-11 w-11 place-items-center rounded-xl ${iconClass}`}>{icon}</div>
      <h2 className="mt-4 text-lg font-black">{title}</h2>
      <p className="mt-2 min-h-[72px] text-sm leading-6 text-white/60">{text}</p>
      <Link href={href} className={`mt-4 inline-flex items-center gap-2 text-sm font-bold ${accent}`}>{link} <ArrowRight size={15} /></Link>
    </article>
  );
}
