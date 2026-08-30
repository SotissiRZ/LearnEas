import Link from "next/link";
import Image from "next/image";
import { ArrowRight, ShieldCheck, Infinity as InfinityIcon, Award, Sparkles } from "lucide-react";
import { safeGet } from "@/lib/api";
import { Category, Course, PDFProduct } from "@/types";
import CourseCard from "@/components/course/CourseCard";
import PdfCard from "@/components/pdf/PdfCard";
import CategoryIcon from "@/components/ui/CategoryIcon";
import ApiErrorBanner from "@/components/ui/ApiErrorBanner";

export default async function HomePage() {
  const [categoriesResult, featuredResult, pdfsResult] = await Promise.all([
    safeGet<Category[]>("/catalog/categories/", []),
    safeGet<Course[]>("/catalog/courses/featured/", []),
    safeGet<{ results: PDFProduct[] }>("/catalog/pdfs/?ordering=-created_at", { results: [] }),
  ]);
  const categories = categoriesResult.data;
  const featuredCourses = featuredResult.data;
  const pdfs = pdfsResult.data;
  const hasError = !categoriesResult.ok || !featuredResult.ok || !pdfsResult.ok;

  return (
    <div>
      {hasError && (
        <div className="container-app pt-6">
          <ApiErrorBanner message={categoriesResult.error || featuredResult.error || pdfsResult.error} />
        </div>
      )}
      {/* HERO */}
      <section className="relative overflow-hidden bg-ink text-white">
        <Image
          src="/images/hero-background.png"
          alt=""
          fill
          priority
          sizes="100vw"
          className="object-contain object-center"
        />
        {/* Voile sombre pour garantir la lisibilité du texte quel que soit le contenu de l'image */}
        <div className="absolute inset-0 bg-gradient-to-r from-ink via-ink/90 to-ink/50" />
        <div className="absolute inset-0 bg-ink/30" />
        <div className="container-app relative z-10 flex flex-col items-center gap-8 py-20 text-center lg:py-28">
          <span className="badge bg-white/10 text-brand-200">
            <Sparkles size={14} /> La plateforme de formation en ligne pensée pour l'Afrique
          </span>
          <h1 className="max-w-3xl text-4xl font-extrabold leading-tight sm:text-5xl">
            Apprenez une compétence entière,
            <span className="text-brand-400"> pas juste une vidéo.</span>
          </h1>
          <p className="max-w-2xl text-lg text-gray-300">
            Cours complets, formations interactives en direct et PDF détaillés · accessibles partout
            en Afrique. Le paiement par carte est traité de manière sécurisée via Stripe ;
            d’autres moyens locaux pourront être activés lorsqu’ils seront réellement intégrés.
          </p>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <Link href="/courses" className="btn-primary !px-6 !py-3 text-base">
              Explorer les cours <ArrowRight size={18} />
            </Link>
            <Link href="/formations" className="btn-outline !border-white/20 !bg-white/5 !px-6 !py-3 text-base !text-white hover:!bg-white/10">
              Formations en direct
            </Link>
            <Link href="/pdfs" className="btn-outline !border-white/20 !bg-white/5 !px-6 !py-3 text-base !text-white hover:!bg-white/10">
              Explorer les PDF
            </Link>
          </div>

          <div className="mt-6 grid w-full max-w-3xl grid-cols-1 gap-3 text-left sm:grid-cols-3 sm:gap-4">
            <div className="rounded-xl2 bg-white/5 p-4">
              <InfinityIcon className="mb-2 text-brand-400" size={22} />
              <p className="text-sm text-gray-300">Accès à vie au cours acheté</p>
            </div>
            <div className="rounded-xl2 bg-white/5 p-4">
              <Award className="mb-2 text-brand-400" size={22} />
              <p className="text-sm text-gray-300">Certificat de fin de formation</p>
            </div>
            <div className="rounded-xl2 bg-white/5 p-4">
              <ShieldCheck className="mb-2 text-brand-400" size={22} />
              <p className="text-sm text-gray-300">Paiement carte sécurisé via Stripe</p>
            </div>
          </div>
        </div>
      </section>

      {/* CATEGORIES */}
      {categories.length > 0 && (
        <section className="container-app py-14">
          <h2 className="mb-6 text-2xl font-extrabold">Parcourir par catégorie</h2>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
            {categories.map((c) => (
              <Link
                key={c.id}
                href={`/courses?category=${c.slug}`}
                className="card flex flex-col items-center gap-2 p-5 text-center transition hover:-translate-y-1 hover:border-brand-200 hover:shadow-soft"
              >
                <div className="grid h-11 w-11 place-items-center rounded-xl bg-brand-50 text-brand-600">
                  <CategoryIcon name={c.icon} size={22} />
                </div>
                <span className="text-sm font-semibold">{c.name}</span>
                <span className="text-xs text-gray-400">{c.courses_count} cours</span>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* FEATURED COURSES */}
      <section className="bg-gray-50 py-14">
        <div className="container-app">
          <div className="mb-6 flex items-center justify-between">
            <h2 className="text-2xl font-extrabold">Cours à la une</h2>
            <Link href="/courses" className="flex items-center gap-1 text-sm font-semibold text-brand-700">
              Voir tout <ArrowRight size={16} />
            </Link>
          </div>
          {featuredCourses.length === 0 ? (
            <p className="text-gray-500">Aucun cours disponible pour le moment.</p>
          ) : (
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {featuredCourses.map((c) => <CourseCard key={c.id} course={c} />)}
            </div>
          )}
        </div>
      </section>

      {/* FEATURED PDFS */}
      <section className="container-app py-14">
        <div className="mb-6 flex items-center justify-between">
          <h2 className="text-2xl font-extrabold">PDF & Guides populaires</h2>
          <Link href="/pdfs" className="flex items-center gap-1 text-sm font-semibold text-brand-700">
            Voir tout <ArrowRight size={16} />
          </Link>
        </div>
        {pdfs.results.length === 0 ? (
          <p className="text-gray-500">Aucun PDF disponible pour le moment.</p>
        ) : (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {pdfs.results.slice(0, 8).map((p) => <PdfCard key={p.id} pdf={p} />)}
          </div>
        )}
      </section>

      {/* CTA INSTRUCTOR */}
      <section className="bg-brand-700">
        <div className="container-app flex flex-col items-center gap-4 py-14 text-center text-white">
          <h2 className="text-2xl font-extrabold sm:text-3xl">Vous avez une expertise à partager ?</h2>
          <p className="max-w-xl text-brand-100">
            Devenez instructeur sur LearnEas : publiez vos cours vidéo et vos PDF, et gardez la main sur votre contenu.
          </p>
          <Link href="/dashboard/instructor" className="btn-primary !bg-white !text-brand-700 hover:!bg-gray-100">
            Devenir instructeur
          </Link>
        </div>
      </section>
    </div>
  );
}
