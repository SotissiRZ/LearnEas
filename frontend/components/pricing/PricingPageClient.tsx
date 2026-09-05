"use client";

import Link from "next/link";
import {
  BadgeCheck, BookOpen, BriefcaseBusiness, Building2, Check, CircleDollarSign,
  GraduationCap, Handshake, ShieldCheck, Sparkles, UsersRound,
} from "lucide-react";
import CurrencyPrice from "@/components/ui/CurrencyPrice";

export type PublicPricingSettings = {
  pricing_enabled: boolean;
  platform_commission_percent: number;
  instructor_pro_monthly_eur: string;
  instructor_pro_commission_percent: number;
  mentor_commission_percent: number;
  employer_free_active_jobs: number;
  employer_single_post_eur: string;
  employer_pro_monthly_eur: string;
  employer_pro_active_jobs: number;
  employer_business_monthly_eur: string;
  employer_business_active_jobs: number;
};

function Feature({ children }: { children: React.ReactNode }) {
  return (
    <li className="flex items-start gap-2.5 text-sm leading-6 text-slate-600">
      <span className="mt-1 grid h-5 w-5 shrink-0 place-items-center rounded-full bg-emerald-50 text-emerald-600"><Check size={13} strokeWidth={3} /></span>
      <span>{children}</span>
    </li>
  );
}

function Price({ value, suffix }: { value: string | number; suffix?: string }) {
  return (
    <div className="flex flex-wrap items-end gap-2">
      <span className="text-3xl font-black tracking-tight text-navy-950"><CurrencyPrice value={value} /></span>
      {suffix && <span className="pb-1 text-sm font-semibold text-slate-500">{suffix}</span>}
    </div>
  );
}

function PlanCard({
  title, eyebrow, price, priceLabel, suffix, badge, featured, children, cta, href,
}: {
  title: string; eyebrow?: string; price?: string | number; priceLabel?: string; suffix?: string; badge?: string; featured?: boolean;
  children: React.ReactNode; cta: string; href: string;
}) {
  return (
    <article className={`relative flex h-full flex-col rounded-3xl border bg-white p-6 shadow-sm transition hover:-translate-y-0.5 hover:shadow-lg ${featured ? "border-brand-400 ring-2 ring-brand-100" : "border-slate-200"}`}>
      {badge && <span className="absolute right-5 top-5 rounded-full bg-brand-50 px-3 py-1 text-[11px] font-black uppercase tracking-wide text-brand-700">{badge}</span>}
      {eyebrow && <p className="mb-2 text-xs font-black uppercase tracking-[.14em] text-brand-600">{eyebrow}</p>}
      <h3 className="pr-20 text-xl font-black text-navy-950">{title}</h3>
      <div className="mt-4">{priceLabel ? <div className="text-2xl font-black tracking-tight text-navy-950">{priceLabel}</div> : <Price value={price ?? 0} suffix={suffix} />}</div>
      <ul className="mt-5 flex-1 space-y-2.5">{children}</ul>
      <Link href={href} className={featured ? "btn-primary mt-6 w-full" : "btn-outline mt-6 w-full"}>{cta}</Link>
    </article>
  );
}

export default function PricingPageClient({ settings }: { settings: PublicPricingSettings }) {
  if (!settings.pricing_enabled) {
    return (
      <main className="bg-slate-50 py-24">
        <div className="container-app text-center">
          <CircleDollarSign className="mx-auto text-brand-500" size={44} />
          <h1 className="mt-4 text-3xl font-black text-navy-950">Tarifs temporairement indisponibles</h1>
          <p className="mx-auto mt-3 max-w-xl text-slate-600">La grille tarifaire est en cours de mise à jour. Contactez-nous pour une proposition adaptée.</p>
          <Link href="/contact" className="btn-primary mt-7">Nous contacter</Link>
        </div>
      </main>
    );
  }

  return (
    <main className="bg-slate-50">
      <section className="relative overflow-hidden bg-navy-950 py-16 text-white sm:py-20">
        <div className="absolute inset-0 bg-hero-radial opacity-80" />
        <div className="container-app relative text-center">
          <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-bold text-white/80"><Sparkles size={14} className="text-brand-400" /> Tarifs de lancement</span>
          <h1 className="mx-auto mt-5 max-w-4xl text-4xl font-black tracking-tight sm:text-5xl">Un modèle simple, transparent et adapté à chaque profil</h1>
          <p className="mx-auto mt-5 max-w-3xl text-base leading-7 text-white/65 sm:text-lg">Pas d’abonnement obligatoire pour apprendre. Vous payez les contenus ou services que vous choisissez, tandis que les créateurs et recruteurs disposent d’offres adaptées à leur activité.</p>
          <div className="mt-7 flex flex-wrap justify-center gap-2 text-xs font-bold text-white/70">
            <a href="#apprenants" className="rounded-full border border-white/15 px-4 py-2 hover:bg-white/10">Apprenants</a>
            <a href="#instructeurs" className="rounded-full border border-white/15 px-4 py-2 hover:bg-white/10">Instructeurs</a>
            <a href="#mentors" className="rounded-full border border-white/15 px-4 py-2 hover:bg-white/10">Mentors</a>
            <a href="#entreprises" className="rounded-full border border-white/15 px-4 py-2 hover:bg-white/10">Entreprises</a>
          </div>
        </div>
      </section>

      <section id="apprenants" className="scroll-mt-28 py-14">
        <div className="container-app">
          <AudienceHeader icon={<GraduationCap size={22} />} title="Apprenants" text="Commencez gratuitement et payez uniquement ce que vous utilisez." />
          <div className="mt-7 grid gap-5 lg:grid-cols-3">
            <PlanCard title="Compte KalanPro" eyebrow="Accès plateforme" price={0} suffix="/ mois" badge="Sans engagement" cta="Créer un compte" href="/register">
              <Feature>Création du profil et accès au catalogue gratuits.</Feature>
              <Feature>Accès aux cours et ressources signalés comme gratuits.</Feature>
              <Feature>Portfolio, candidatures et vérification des certificats.</Feature>
            </PlanCard>
            <PlanCard title="Formations & ressources" eyebrow="À la carte" priceLabel="Prix affiché par contenu" cta="Voir les formations" href="/courses" featured>
              <Feature>Cours vidéo, PDF et cohortes au prix affiché par le créateur.</Feature>
              <Feature>Aucun abonnement mensuel obligatoire pour acheter.</Feature>
              <Feature>Certificat inclus lorsqu’il est prévu par la formation.</Feature>
            </PlanCard>
            <PlanCard title="Mentorat" eyebrow="À la séance" priceLabel="Prix fixé par le mentor" cta="Trouver un mentor" href="/mentorship">
              <Feature>Le mentor fixe son tarif par séance ou accompagnement.</Feature>
              <Feature>Vous connaissez le prix avant la réservation.</Feature>
              <Feature>Historique et suivi depuis votre espace KalanPro.</Feature>
            </PlanCard>
          </div>
        </div>
      </section>

      <section id="instructeurs" className="scroll-mt-28 border-y border-slate-200 bg-white py-14">
        <div className="container-app">
          <AudienceHeader icon={<BookOpen size={22} />} title="Instructeurs" text="Publiez sans frais fixes, puis choisissez le niveau de service adapté à votre volume de ventes." />
          <div className="mt-7 grid gap-5 lg:grid-cols-2">
            <PlanCard title="Standard" eyebrow="Sans abonnement" price={0} suffix="/ mois" badge={`${settings.platform_commission_percent}% de commission`} cta="Devenir instructeur" href="/become-instructor">
              <Feature>Publication de cours, PDF et cohortes.</Feature>
              <Feature>Commission KalanPro : <strong>{settings.platform_commission_percent}%</strong> sur chaque vente encaissée.</Feature>
              <Feature>HLS faible connexion, certificats, projets et statistiques essentielles.</Feature>
            </PlanCard>
            <PlanCard title="Pro créateur" eyebrow="Pour les créateurs actifs" price={settings.instructor_pro_monthly_eur} suffix="/ mois" badge="Sur demande" featured cta="Parler à l’équipe" href="/contact?subject=KalanPro%20Pro%20instructeur">
              <Feature>Commission réduite à <strong>{settings.instructor_pro_commission_percent}%</strong>.</Feature>
              <Feature>Positionnement prioritaire dans les opérations commerciales KalanPro.</Feature>
              <Feature>Accompagnement et support prioritaire.</Feature>
              <Feature>Activation commerciale sur demande pendant la phase de lancement.</Feature>
            </PlanCard>
          </div>
        </div>
      </section>

      <section id="mentors" className="scroll-mt-28 py-14">
        <div className="container-app">
          <AudienceHeader icon={<Handshake size={22} />} title="Mentors" text="Fixez votre prix, KalanPro ne gagne que lorsque vous réalisez une séance payante." />
          <div className="mt-7 grid gap-5 lg:grid-cols-2">
            <PlanCard title="Mentor KalanPro" eyebrow="Marketplace" price={0} suffix="/ mois" badge={`${settings.mentor_commission_percent}% de commission`} cta="Proposer du mentorat" href="/become-instructor" featured>
              <Feature>Aucun frais mensuel pour référencer votre offre.</Feature>
              <Feature>Vous définissez librement le prix de vos séances.</Feature>
              <Feature>Commission KalanPro : <strong>{settings.mentor_commission_percent}%</strong> sur les séances encaissées.</Feature>
            </PlanCard>
            <div className="rounded-3xl border border-slate-200 bg-navy-950 p-7 text-white">
              <UsersRound className="text-brand-400" size={32} />
              <h3 className="mt-5 text-2xl font-black">Pourquoi ce modèle ?</h3>
              <p className="mt-3 leading-7 text-white/65">Il permet de démarrer sans risque financier : pas de coût fixe tant que vous ne générez pas de revenu sur KalanPro.</p>
              <div className="mt-6 rounded-2xl border border-white/10 bg-white/5 p-4 text-sm leading-6 text-white/70">La commission finance le paiement, l’infrastructure, le support, les outils de visioconférence et l’acquisition d’apprenants.</div>
            </div>
          </div>
        </div>
      </section>

      <section id="entreprises" className="scroll-mt-28 border-y border-slate-200 bg-white py-14">
        <div className="container-app">
          <AudienceHeader icon={<Building2 size={22} />} title="Entreprises & recruteurs" text="Commencez gratuitement, puis augmentez votre capacité de recrutement selon vos besoins." />
          <div className="mt-7 grid gap-5 md:grid-cols-2 xl:grid-cols-4">
            <PlanCard title="Starter" eyebrow="Découverte" price={0} suffix="/ mois" cta="Créer l’espace recruteur" href="/dashboard/employer">
              <Feature>Profil entreprise vérifié.</Feature>
              <Feature>Jusqu’à <strong>{settings.employer_free_active_jobs}</strong> offre active.</Feature>
              <Feature>Réception et suivi des candidatures KalanPro.</Feature>
            </PlanCard>
            <PlanCard title="Annonce à l’unité" eyebrow="Besoin ponctuel" price={settings.employer_single_post_eur} suffix="/ annonce · 30 jours" cta="Acheter l’annonce" href="/checkout?employer_product=single_post">
              <Feature>Une annonce professionnelle pendant 30 jours.</Feature>
              <Feature>Idéal si vous recrutez occasionnellement.</Feature>
              <Feature>Accès aux candidatures reçues pour cette annonce.</Feature>
            </PlanCard>
            <PlanCard title="Pro recrutement" eyebrow="Équipe en croissance" price={settings.employer_pro_monthly_eur} suffix="/ mois" badge="Recommandé" featured cta="Activer Pro" href="/checkout?employer_product=pro">
              <Feature>Jusqu’à <strong>{settings.employer_pro_active_jobs}</strong> offres actives.</Feature>
              <Feature>Accès au vivier de profils ayant choisi d’être visibles.</Feature>
              <Feature>Suivi centralisé des candidatures et de leur statut.</Feature>
            </PlanCard>
            <PlanCard title="Business" eyebrow="Recrutement régulier" price={settings.employer_business_monthly_eur} suffix="/ mois" cta="Activer Business" href="/checkout?employer_product=business">
              <Feature>Jusqu’à <strong>{settings.employer_business_active_jobs}</strong> offres actives.</Feature>
              <Feature>Accompagnement commercial et support prioritaire.</Feature>
              <Feature>Options de visibilité renforcée selon les campagnes.</Feature>
            </PlanCard>
          </div>
          <p className="mt-5 text-center text-xs leading-5 text-slate-500">Les achats recruteur sont activés depuis le checkout KalanPro. Les périodes Pro et Business durent 30 jours et les renouvellements successifs sont chaînés sans chevauchement.</p>
        </div>
      </section>

      <section className="py-14">
        <div className="container-app grid gap-5 lg:grid-cols-3">
          <InfoBox icon={<ShieldCheck size={22} />} title="Prix transparents">Le montant du contenu ou du service est affiché avant paiement. Les frais des prestataires de paiement ou taxes légalement applicables peuvent dépendre du pays et du moyen de paiement.</InfoBox>
          <InfoBox icon={<CircleDollarSign size={22} />} title="Devise locale">Utilisez le sélecteur de devise dans la barre de navigation pour afficher les montants dans une devise disponible, notamment XOF/XAF lorsqu’ils sont activés.</InfoBox>
          <InfoBox icon={<BadgeCheck size={22} />} title="Tarifs administrables">Les prix des offres commerciales et les taux de commission peuvent être modifiés par l’administrateur KalanPro sans redéployer le site.</InfoBox>
        </div>
      </section>

      <section className="bg-navy-950 py-14 text-white">
        <div className="container-app flex flex-col items-center justify-between gap-6 text-center lg:flex-row lg:text-left">
          <div><h2 className="text-3xl font-black">Besoin d’une offre sur mesure ?</h2><p className="mt-2 text-white/60">École, ONG, entreprise ou programme de formation : parlons de votre volume et de vos besoins.</p></div>
          <Link href="/contact" className="btn-primary shrink-0">Demander une proposition</Link>
        </div>
      </section>
    </main>
  );
}

function AudienceHeader({ icon, title, text }: { icon: React.ReactNode; title: string; text: string }) {
  return (
    <div className="flex max-w-3xl items-start gap-4">
      <span className="grid h-11 w-11 shrink-0 place-items-center rounded-2xl bg-brand-50 text-brand-600">{icon}</span>
      <div><h2 className="text-2xl font-black text-navy-950 sm:text-3xl">{title}</h2><p className="mt-2 text-sm leading-6 text-slate-600 sm:text-base">{text}</p></div>
    </div>
  );
}

function InfoBox({ icon, title, children }: { icon: React.ReactNode; title: string; children: React.ReactNode }) {
  return <div className="rounded-2xl border border-slate-200 bg-white p-5"><span className="text-brand-600">{icon}</span><h3 className="mt-3 font-black text-navy-950">{title}</h3><p className="mt-2 text-sm leading-6 text-slate-600">{children}</p></div>;
}
