"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, BriefcaseBusiness, Building2, ExternalLink, Globe2, MapPin, ShieldCheck, Sparkles, UsersRound } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import OpportunityCard from "@/components/opportunities/OpportunityCard";
import type { EmployerProfile, Opportunity } from "@/types/opportunities";

type Paginated<T> = { count: number; results: T[] };

export default function CompanyPublicPage() {
  const { slug } = useParams<{ slug: string }>();
  const [company, setCompany] = useState<EmployerProfile | null>(null);
  const [jobs, setJobs] = useState<Opportunity[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!slug) return;
    Promise.all([
      api.get<EmployerProfile>(`/opportunities/companies/${slug}/`),
      api.get<Paginated<Opportunity> | Opportunity[]>(`/opportunities/listings/?employer=${encodeURIComponent(slug)}&page_size=30`),
    ]).then(([profile, listings]) => {
      setCompany(profile); setJobs(Array.isArray(listings) ? listings : listings.results);
    }).catch((e) => setError(e instanceof ApiError ? e.message : "Entreprise introuvable."));
  }, [slug]);

  if (error) return <div className="container-app py-14"><div className="card p-8 text-red-700">{error}</div></div>;
  if (!company) return <div className="container-app py-14 text-slate-500">Chargement de l'entreprise...</div>;

  return <div className="pb-14">
    <section className="relative min-h-[330px] overflow-hidden bg-gradient-to-br from-[#061a38] via-[#0d2d5f] to-[#184987] bg-cover bg-center" style={company.banner ? { backgroundImage: `linear-gradient(90deg,rgba(3,15,37,.86),rgba(3,15,37,.38)),url(${company.banner})` } : undefined}>
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_82%_20%,rgba(255,104,39,.22),transparent_30%)]" />
      <div className="container-app relative py-9 text-white sm:py-12"><Link href="/opportunities" className="inline-flex items-center gap-2 text-sm font-semibold text-blue-100 hover:text-white"><ArrowLeft size={15}/> Retour aux opportunités</Link><div className="mt-10 flex flex-col gap-5 sm:flex-row sm:items-end"><div className="grid h-24 w-24 shrink-0 place-items-center overflow-hidden rounded-2xl border-4 border-white bg-white shadow-xl sm:h-28 sm:w-28">{company.logo ? <img loading="lazy" decoding="async" src={company.logo} alt={`Logo ${company.company_name}`} className="h-full w-full object-contain p-1"/> : <Building2 size={38} className="text-slate-500"/>}</div><div><div className="flex flex-wrap gap-2"><span className="rounded-full bg-emerald-400/20 px-2.5 py-1 text-[11px] font-bold text-emerald-100"><ShieldCheck size={12} className="mr-1 inline"/> Entreprise vérifiée</span>{company.industry && <span className="rounded-full bg-white/10 px-2.5 py-1 text-[11px] font-semibold">{company.industry}</span>}</div><h1 className="mt-3 text-3xl font-extrabold sm:text-4xl">{company.company_name}</h1><p className="mt-2 max-w-3xl text-sm text-blue-100 sm:text-base">{company.tagline || "Découvrez l'entreprise, sa culture et ses opportunités sur KalanPro."}</p><div className="mt-4 flex flex-wrap gap-4 text-xs text-blue-100">{(company.city || company.country) && <span className="flex items-center gap-1"><MapPin size={13}/>{[company.city, company.country].filter(Boolean).join(", ")}</span>}{company.company_size && <span className="flex items-center gap-1"><UsersRound size={13}/>{company.company_size}</span>}{company.founded_year && <span>Créée en {company.founded_year}</span>}<span>{jobs.length} opportunité(s) ouverte(s)</span></div></div></div></div>
    </section>

    <div className="container-app mt-8 grid gap-7 lg:grid-cols-[minmax(0,1fr)_330px]">
      <main className="space-y-7"><section className="card p-6 sm:p-7"><h2 className="text-xl font-extrabold">À propos</h2><p className="mt-4 whitespace-pre-line text-sm leading-7 text-slate-600">{company.description || "Cette entreprise n'a pas encore complété sa présentation."}</p></section>{company.values && company.values.length > 0 && <section className="card p-6 sm:p-7"><h2 className="flex items-center gap-2 text-xl font-extrabold"><Sparkles size={19} className="text-orange-600"/> Nos valeurs</h2><div className="mt-4 flex flex-wrap gap-2">{company.values.map((value) => <span key={value} className="rounded-full border border-orange-100 bg-orange-50 px-3 py-2 text-xs font-semibold text-orange-800">{value}</span>)}</div></section>}{company.benefits && company.benefits.length > 0 && <section className="card p-6 sm:p-7"><h2 className="text-xl font-extrabold">Pourquoi nous rejoindre ?</h2><div className="mt-4 grid gap-3 sm:grid-cols-2">{company.benefits.map((benefit) => <div key={benefit} className="rounded-2xl bg-slate-50 p-4 text-sm font-medium text-slate-700"><span className="mr-2 text-orange-600">✓</span>{benefit}</div>)}</div></section>}<section><div className="mb-4 flex items-end justify-between"><div><p className="text-xs font-bold uppercase tracking-wider text-orange-600">Recrutement</p><h2 className="mt-1 text-2xl font-extrabold">Opportunités chez {company.company_name}</h2></div></div>{jobs.length ? <div className="catalog-grid">{jobs.map((job) => <OpportunityCard key={job.id} opportunity={job}/>)}</div> : <EmptyCompanyJobs />}</section></main>
      <aside className="space-y-4 lg:sticky lg:top-24 lg:self-start"><section className="card p-5"><h3 className="font-extrabold">Informations entreprise</h3><div className="mt-4 space-y-3 text-sm text-slate-600">{company.industry && <p><strong className="text-slate-900">Secteur :</strong> {company.industry}</p>}{company.company_size && <p><strong className="text-slate-900">Taille :</strong> {company.company_size}</p>}{company.hiring_regions && company.hiring_regions.length > 0 && <div><strong className="text-slate-900">Recrute dans :</strong><div className="mt-2 flex flex-wrap gap-1.5">{company.hiring_regions.map((region) => <span key={region} className="rounded-full bg-slate-100 px-2 py-1 text-[10px]">{region}</span>)}</div></div>}</div><div className="mt-5 space-y-2">{company.website_url && <a href={company.website_url} target="_blank" rel="noreferrer" className="btn-outline w-full"><Globe2 size={14}/> Site web <ExternalLink size={12}/></a>}{company.linkedin_url && <a href={company.linkedin_url} target="_blank" rel="noreferrer" className="btn-outline w-full"><BriefcaseBusiness size={14}/> LinkedIn <ExternalLink size={12}/></a>}</div></section></aside>
    </div>
  </div>;
}

function EmptyCompanyJobs() { return <div className="rounded-2xl border border-dashed border-slate-200 bg-white p-10 text-center"><BriefcaseBusiness size={28} className="mx-auto text-slate-300"/><p className="mt-3 text-sm font-semibold text-slate-600">Aucune opportunité ouverte actuellement.</p></div>; }
