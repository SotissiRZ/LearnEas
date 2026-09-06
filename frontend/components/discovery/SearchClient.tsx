"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  BookOpen, BriefcaseBusiness, Building2, FileText, GraduationCap, Search,
  Sparkles, UserRoundSearch, UsersRound, MapPin, Star, WifiOff,
} from "lucide-react";
import { api, ApiError } from "@/lib/api";
import type { DiscoveryKind, DiscoveryResult, GlobalSearchResponse, RecommendationResponse } from "@/types/discovery";
import { trackProductEvent } from "@/lib/analytics";

const FILTERS: Array<{ value: "all" | DiscoveryKind; label: string }> = [
  { value: "all", label: "Tout" }, { value: "course", label: "Cours" },
  { value: "formation", label: "Formations" }, { value: "pdf", label: "PDF" },
  { value: "mentor", label: "Mentors" }, { value: "opportunity", label: "Opportunités" },
  { value: "company", label: "Entreprises" }, { value: "talent", label: "Talents" },
];

const KIND_LABEL: Record<DiscoveryKind, string> = {
  course: "Cours", formation: "Formation", pdf: "PDF", mentor: "Mentorat",
  opportunity: "Opportunité", company: "Entreprise", talent: "Talent",
};

export default function SearchClient({ initialQuery }: { initialQuery: string }) {
  const router = useRouter();
  const [input, setInput] = useState(initialQuery);
  const [query, setQuery] = useState(initialQuery.trim());
  const [active, setActive] = useState<"all" | DiscoveryKind>("all");
  const [data, setData] = useState<GlobalSearchResponse | null>(null);
  const [recommendations, setRecommendations] = useState<RecommendationResponse | null>(null);
  const [loading, setLoading] = useState(Boolean(initialQuery.trim()));
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    if (!query) {
      setData(null); setError(""); setLoading(false);
      api.get<RecommendationResponse>("/discovery/recommendations/?limit=6")
        .then((payload) => { if (!cancelled) setRecommendations(payload); })
        .catch(() => { if (!cancelled) setRecommendations(null); });
      return () => { cancelled = true; };
    }
    if (query.length < 2) return () => { cancelled = true; };
    setLoading(true); setError("");
    const typeParam = active === "all" ? "" : `&types=${encodeURIComponent(active)}`;
    api.get<GlobalSearchResponse>(`/discovery/search/?q=${encodeURIComponent(query)}&limit=10${typeParam}`)
      .then((payload) => { if (!cancelled) setData(payload); })
      .catch((err) => { if (!cancelled) setError(err instanceof ApiError ? err.message : "Recherche indisponible."); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [query, active]);

  function submit(event: React.FormEvent) {
    event.preventDefault();
    const value = input.trim().slice(0, 120);
    if (value.length === 1) { setError("Saisissez au moins 2 caractères."); return; }
    setQuery(value); setActive("all");
    if (value) trackProductEvent("search_submitted", { query_length: value.length, source: "search_page" }, "/search");
    router.replace(value ? `/search?q=${encodeURIComponent(value)}` : "/search", { scroll: false });
  }

  const visibleFilters = useMemo(() => {
    if (!data) return FILTERS.filter((item) => item.value !== "talent");
    return FILTERS.filter((item) => item.value !== "talent" || data.available_types.includes("talent"));
  }, [data]);

  return (
    <main className="min-h-screen bg-slate-50 pb-20 pt-28">
      <section className="border-b border-slate-200 bg-white">
        <div className="mx-auto w-full max-w-7xl px-4 py-10 sm:px-6 lg:px-8">
          <p className="text-xs font-black uppercase tracking-[.18em] text-brand-600">Découvrir KalanPro</p>
          <h1 className="mt-2 text-3xl font-black tracking-tight text-navy-950 sm:text-4xl">Une recherche pour toute la plateforme</h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600 sm:text-base">Cours, cohortes, PDF, mentors, entreprises et opportunités sont classés ensemble selon la pertinence.</p>
          <form onSubmit={submit} className="mt-7 flex max-w-4xl gap-2">
            <div className="relative min-w-0 flex-1">
              <Search size={20} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
              <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ex. Python, comptabilité, Dakar, designer..." className="w-full rounded-2xl border border-slate-300 bg-white py-3.5 pl-12 pr-4 text-sm outline-none transition focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10" />
            </div>
            <button className="rounded-2xl bg-brand-500 px-5 py-3 text-sm font-black text-white shadow-sm hover:bg-brand-600">Rechercher</button>
          </form>
          {query && <div className="mt-5 flex gap-2 overflow-x-auto pb-1">{visibleFilters.map((item) => <button key={item.value} onClick={() => setActive(item.value)} className={`whitespace-nowrap rounded-full border px-4 py-2 text-xs font-bold transition ${active === item.value ? "border-navy-950 bg-navy-950 text-white" : "border-slate-200 bg-white text-slate-600 hover:border-slate-400"}`}>{item.label}</button>)}</div>}
        </div>
      </section>

      <div className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        {error && <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm font-semibold text-red-700">{error}</div>}
        {loading && <LoadingGrid />}
        {!loading && query && data && <SearchResults data={data} active={active} />}
        {!query && !loading && <RecommendationSections data={recommendations} />}
      </div>
    </main>
  );
}

function SearchResults({ data, active }: { data: GlobalSearchResponse; active: "all" | DiscoveryKind }) {
  const sections = active === "all" ? data.types : [active];
  const total = sections.reduce((sum, type) => sum + (data.groups[type]?.length || 0), 0);
  if (!total) return <EmptyState />;
  return <div className="space-y-10">
    <div><p className="text-sm font-bold text-slate-500">Résultats pour</p><h2 className="mt-1 text-2xl font-black text-navy-950">« {data.query} »</h2></div>
    {sections.map((type) => {
      const rows = data.groups[type] || [];
      if (!rows.length) return null;
      return <section key={type}><div className="mb-4 flex items-center gap-2"><KindIcon type={type} /><h3 className="text-lg font-black text-navy-950">{KIND_LABEL[type]}</h3><span className="rounded-full bg-slate-200 px-2 py-0.5 text-[11px] font-black text-slate-600">{rows.length}</span></div><div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{rows.map((row) => <ResultCard key={`${row.type}-${row.id}`} row={row} source="search" />)}</div></section>;
    })}
  </div>;
}

function RecommendationSections({ data }: { data: RecommendationResponse | null }) {
  if (!data) return <div className="rounded-3xl border border-slate-200 bg-white p-8 text-sm text-slate-500">Utilisez la recherche pour explorer KalanPro.</div>;
  const sections = [
    { title: "Pour continuer à progresser", rows: data.learning, icon: <Sparkles size={19} className="text-brand-500" /> },
    { title: "Opportunités recommandées", rows: data.opportunities, icon: <BriefcaseBusiness size={19} className="text-brand-500" /> },
    { title: "Talents recommandés", rows: data.talents, icon: <UserRoundSearch size={19} className="text-brand-500" /> },
  ].filter((section) => section.rows.length > 0);
  return <div className="space-y-10">
    <div className="rounded-3xl border border-brand-100 bg-gradient-to-br from-brand-50 to-white p-6"><div className="flex items-center gap-2 text-brand-700"><Sparkles size={18} /><span className="text-xs font-black uppercase tracking-[.14em]">Recommandations</span></div><h2 className="mt-2 text-2xl font-black text-navy-950">{data.personalized ? "Sélection adaptée à votre profil" : "À découvrir sur KalanPro"}</h2>{data.signals.length > 0 && <p className="mt-2 text-sm text-slate-600">Signaux utilisés : {data.signals.slice(0, 5).join(" · ")}</p>}</div>
    {sections.map((section) => <section key={section.title}><div className="mb-4 flex items-center gap-2">{section.icon}<h3 className="text-lg font-black text-navy-950">{section.title}</h3></div><div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{section.rows.map((row) => <ResultCard key={`${row.type}-${row.id}`} row={row} source="recommendation" />)}</div></section>)}
  </div>;
}

function ResultCard({ row, source }: { row: DiscoveryResult; source: "search" | "recommendation" }) {
  const location = [row.meta.city, row.meta.country].filter(Boolean).join(", ");
  const price = typeof row.meta.price === "number" ? (row.meta.price === 0 ? "Gratuit" : `${row.meta.price.toLocaleString("fr-FR")} €`) : null;
  const match = typeof row.meta.match_score === "number" ? row.meta.match_score : null;
  return <Link href={row.url} onClick={() => trackProductEvent(source === "recommendation" ? "recommendation_clicked" : "discovery_result_clicked", { result_type: row.type, result_id: row.id, source }, "/search")} className="group overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm transition hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-md">
    <div className="flex min-h-32 gap-4 p-4">
      <div className="grid h-24 w-24 shrink-0 place-items-center overflow-hidden rounded-2xl bg-slate-100">
        {row.image ? <img src={row.image} alt="" loading="lazy" decoding="async" className="h-full w-full object-cover" /> : <KindIcon type={row.type} large />}
      </div>
      <div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><span className="rounded-full bg-brand-50 px-2 py-1 text-[10px] font-black uppercase tracking-wide text-brand-700">{KIND_LABEL[row.type]}</span>{match !== null && <span className="rounded-full bg-emerald-50 px-2 py-1 text-[10px] font-black text-emerald-700">Match {match}%</span>}</div><h4 className="mt-2 line-clamp-2 text-base font-black leading-5 text-navy-950 group-hover:text-brand-700">{row.title}</h4><p className="mt-1 line-clamp-1 text-xs font-semibold text-slate-500">{row.subtitle}</p>{location && <p className="mt-2 flex items-center gap-1 text-[11px] text-slate-500"><MapPin size={12} />{location}</p>}</div>
    </div>
    <div className="border-t border-slate-100 px-4 py-3"><div className="flex items-center justify-between gap-3 text-xs"><span className="line-clamp-1 text-slate-500">{row.reason || row.description || "Voir les détails"}</span>{price && <span className="shrink-0 font-black text-navy-950">{price}</span>}{typeof row.meta.rating === "number" && Number(row.meta.rating) > 0 && <span className="flex shrink-0 items-center gap-1 font-black text-amber-600"><Star size={12} fill="currentColor" />{Number(row.meta.rating).toFixed(1)}</span>}</div></div>
  </Link>;
}

function KindIcon({ type, large = false }: { type: DiscoveryKind; large?: boolean }) {
  const size = large ? 30 : 18;
  const cls = large ? "text-slate-400" : "text-brand-500";
  const props = { size, className: cls };
  if (type === "course") return <BookOpen {...props} />;
  if (type === "formation") return <GraduationCap {...props} />;
  if (type === "pdf") return <FileText {...props} />;
  if (type === "mentor") return <UsersRound {...props} />;
  if (type === "opportunity") return <BriefcaseBusiness {...props} />;
  if (type === "company") return <Building2 {...props} />;
  return <UserRoundSearch {...props} />;
}

function LoadingGrid() { return <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 6 }).map((_, i) => <div key={i} className="h-36 animate-pulse rounded-3xl border border-slate-200 bg-white p-4"><div className="h-full rounded-2xl bg-slate-100" /></div>)}</div>; }
function EmptyState() { return <div className="rounded-3xl border border-slate-200 bg-white p-10 text-center"><WifiOff className="mx-auto text-slate-300" size={34} /><h2 className="mt-3 text-lg font-black text-navy-950">Aucun résultat pertinent</h2><p className="mt-2 text-sm text-slate-500">Essayez un terme plus général, un métier, une compétence ou un pays.</p></div>; }
