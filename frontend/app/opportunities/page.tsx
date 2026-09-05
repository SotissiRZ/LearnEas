"use client";

import { useEffect, useMemo, useState } from "react";
import { BriefcaseBusiness, Search, SlidersHorizontal } from "lucide-react";
import { api, ApiError } from "@/lib/api";
import CountrySelect from "@/components/ui/CountrySelect";
import OpportunityCard from "@/components/opportunities/OpportunityCard";
import type { Opportunity } from "@/types/opportunities";

type Paginated<T> = { count: number; next: string | null; previous: string | null; results: T[] };

export default function OpportunitiesPage() {
  const [items, setItems] = useState<Opportunity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [kind, setKind] = useState("");
  const [mode, setMode] = useState("");
  const [country, setCountry] = useState("");
  const [level, setLevel] = useState("");

  const query = useMemo(() => {
    const params = new URLSearchParams({ ordering: "-featured,-published_at", page_size: "60" });
    if (search.trim()) params.set("search", search.trim());
    if (kind) params.set("kind", kind);
    if (mode) params.set("work_mode", mode);
    if (country) params.set("country", country);
    if (level) params.set("experience_level", level);
    return params.toString();
  }, [search, kind, mode, country, level]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setLoading(true);
      setError("");
      api.get<Paginated<Opportunity> | Opportunity[]>(`/opportunities/listings/?${query}`)
        .then((data) => setItems(Array.isArray(data) ? data : data.results))
        .catch((e) => setError(e instanceof ApiError ? e.message : "Impossible de charger les opportunités."))
        .finally(() => setLoading(false));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [query]);

  return (
    <div className="container-app py-10">
      <section className="mb-8 rounded-3xl bg-gradient-to-br from-slate-950 via-slate-900 to-brand-950 px-6 py-10 text-white sm:px-10">
        <div className="max-w-3xl">
          <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold"><BriefcaseBusiness size={14} /> KalanPro Opportunités</span>
          <h1 className="mt-4 text-3xl font-extrabold sm:text-4xl">Transformez vos compétences en opportunités professionnelles.</h1>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">Emplois, stages et missions freelance sélectionnés pour les talents d'Afrique francophone. Votre portfolio, vos projets vérifiés et vos certificats renforcent votre candidature.</p>
        </div>
      </section>

      <div className="mb-6 grid gap-3 rounded-2xl border border-gray-100 bg-white p-4 shadow-sm md:grid-cols-2 xl:grid-cols-5">
        <div className="relative md:col-span-2 xl:col-span-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={17} />
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Métier, entreprise, compétence..." className="w-full rounded-lg border border-gray-200 py-2.5 pl-9 pr-3 text-sm" />
        </div>
        <select value={kind} onChange={(e) => setKind(e.target.value)} className="input-admin w-full"><option value="">Tous les formats</option><option value="job">Emploi</option><option value="internship">Stage</option><option value="freelance">Freelance</option><option value="mission">Mission</option></select>
        <select value={mode} onChange={(e) => setMode(e.target.value)} className="input-admin w-full"><option value="">Tous les modes</option><option value="remote">À distance</option><option value="hybrid">Hybride</option><option value="onsite">Sur site</option></select>
        <CountrySelect value={country} onChange={setCountry} emptyLabel="Tous les pays" />
        <select value={level} onChange={(e) => setLevel(e.target.value)} className="input-admin w-full"><option value="">Toute expérience</option><option value="entry">Premier emploi</option><option value="junior">Junior</option><option value="mid">Intermédiaire</option><option value="senior">Senior</option><option value="lead">Lead / management</option></select>
      </div>

      <div className="mb-4 flex items-center justify-between gap-3"><p className="text-sm text-gray-500">{loading ? "Recherche..." : `${items.length} opportunité${items.length > 1 ? "s" : ""}`}</p><span className="flex items-center gap-1 text-xs text-gray-400"><SlidersHorizontal size={13} /> Filtres adaptés au marché local</span></div>
      {error && <div className="mb-5 rounded-xl bg-red-50 p-4 text-sm text-red-700">{error}</div>}
      {!loading && items.length === 0 ? <div className="card p-10 text-center text-gray-500">Aucune opportunité ne correspond actuellement à ces critères.</div> : <div className="catalog-grid">{items.map((item) => <OpportunityCard key={item.id} opportunity={item} />)}</div>}
    </div>
  );
}
