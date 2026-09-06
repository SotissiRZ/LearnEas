"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import {
  Search, ShoppingCart, ChevronDown, LayoutDashboard, BookOpen, FileText, LogOut,
  User as UserIcon, Menu, X, MessageCircle, Wrench, ExternalLink, ClipboardCheck,
  BriefcaseBusiness, Video, Layers3, UsersRound, Building2, GraduationCap, Bot, Bell,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useCart } from "@/hooks/useCart";
import { api } from "@/lib/api";
import CurrencySelector from "@/components/layout/CurrencySelector";
import BrandLogo from "@/components/layout/BrandLogo";
import NotificationBell from "@/components/notifications/NotificationBell";

export default function Navbar() {
  const router = useRouter();
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const items = useCart((s) => s.items);
  const [query, setQuery] = useState("");
  const [searchFocused, setSearchFocused] = useState(false);
  const [suggestions, setSuggestions] = useState<Array<{ type: string; title: string; subtitle: string; url: string }>>([]);
  const [menuOpen, setMenuOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [platform, setPlatform] = useState({ registration_enabled: true });
  const profileMenuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setMenuOpen(false);
    setMobileOpen(false);
  }, [pathname]);

  useEffect(() => {
    api.get<{ registration_enabled: boolean }>("/auth/platform-settings/")
      .then((data) => setPlatform({ registration_enabled: data.registration_enabled }))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    const term = query.trim();
    if (term.length < 2) { setSuggestions([]); return; }
    const timer = window.setTimeout(() => {
      api.get<{ suggestions: Array<{ type: string; title: string; subtitle: string; url: string }> }>(`/discovery/search/suggestions/?q=${encodeURIComponent(term)}`)
        .then((data) => setSuggestions(data.suggestions || []))
        .catch(() => setSuggestions([]));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [query]);

  useEffect(() => {
    function closeOutside(event: MouseEvent) {
      if (menuOpen && profileMenuRef.current && !profileMenuRef.current.contains(event.target as Node)) setMenuOpen(false);
    }
    function closeEscape(event: KeyboardEvent) { if (event.key === "Escape") setMenuOpen(false); }
    document.addEventListener("mousedown", closeOutside);
    document.addEventListener("keydown", closeEscape);
    return () => {
      document.removeEventListener("mousedown", closeOutside);
      document.removeEventListener("keydown", closeEscape);
    };
  }, [menuOpen]);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    const term = query.trim();
    setSuggestions([]);
    setSearchFocused(false);
    router.push(term ? `/search?q=${encodeURIComponent(term)}` : "/search");
  }

  const dashboardHref = user?.role === "admin" ? "/dashboard/admin" : user?.role === "instructor" ? "/dashboard/instructor" : user?.role === "employer" ? "/dashboard/employer" : "/dashboard/student";
  const djangoAdminHref = (process.env.NEXT_PUBLIC_API_URL || "/api").replace(/\/api\/?$/, "/admin/");
  const navLink = "whitespace-nowrap rounded-lg px-3 py-2 text-sm font-semibold text-white/80 transition hover:bg-white/10 hover:text-white";

  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-white/10 bg-navy-950/95 text-white shadow-[0_8px_30px_rgba(6,21,47,.18)] backdrop-blur-xl">
      <div className="mx-auto flex h-20 w-full max-w-[1680px] items-center gap-4 px-5 lg:px-6 2xl:px-8">
        <BrandLogo className="mr-2" />

        <nav className="ml-2 hidden shrink-0 items-center gap-1.5 xl:flex xl:gap-2" aria-label="Navigation principale">
          <DesktopDropdown label="Formations" href="/courses" linkClass={navLink} width="w-[700px]">
            <div className="grid grid-cols-[1.05fr_.95fr] gap-2 p-3">
              <div className="rounded-xl p-2">
                <p className="px-2 pb-2 text-[11px] font-black uppercase tracking-[.14em] text-slate-400">Formats d'apprentissage</p>
                <DropdownItem href="/courses" icon={<BookOpen size={18} />} title="Cours vidéo" text="Playlists complètes, projets et certificats." />
                <DropdownItem href="/pdfs" icon={<FileText size={18} />} title="PDF & Guides" text="Ressources pratiques à consulter hors ligne." />
                <DropdownItem href="/formations" icon={<Video size={18} />} title="Cohortes live" text="Apprentissage en groupe avec séances en direct." />
              </div>
              <div className="rounded-xl bg-slate-50 p-4">
                <div className="mb-3 flex items-center gap-2 text-xs font-black uppercase tracking-[.12em] text-navy-800"><Layers3 size={15} className="text-brand-500" /> Explorer par domaine</div>
                <div className="grid gap-1">
                  <DomainLink href="/courses?domain=technologie-numerique" label="Technologie & Numérique" />
                  <DomainLink href="/courses?domain=data-ia" label="Data & IA" />
                  <DomainLink href="/courses?domain=design-creation" label="Design & Création" />
                  <DomainLink href="/courses?domain=business-gestion" label="Business & Gestion" />
                  <DomainLink href="/courses?domain=bureautique-productivite" label="Bureautique & Productivité" />
                </div>
                <Link href="/courses" className="mt-3 inline-flex items-center gap-1 text-xs font-black text-brand-600 hover:text-brand-700">Voir tout le catalogue <ExternalLink size={12} /></Link>
              </div>
            </div>
          </DesktopDropdown>

          <DesktopDropdown label="Mentorat" href="/mentorship" linkClass={navLink} width="w-[430px]">
            <div className="p-3">
              <DropdownItem href="/mentorship" icon={<UsersRound size={18} />} title="Trouver un mentor" text="Réservez un accompagnement individuel avec un expert." />
              <DropdownItem href="/formations" icon={<GraduationCap size={18} />} title="Apprendre en cohorte" text="Progressez avec un groupe et un formateur en direct." />
              <DropdownItem href="/become-instructor" icon={<UserIcon size={18} />} title="Devenir instructeur" text="Proposez vos cours, cohortes et accompagnements." />
            </div>
          </DesktopDropdown>

          <DesktopDropdown label="Opportunités" href="/opportunities" linkClass={navLink} width="w-[430px]">
            <div className="p-3">
              <DropdownItem href="/opportunities" icon={<BriefcaseBusiness size={18} />} title="Emplois & missions" text="Parcourez les offres adaptées à vos compétences." />
              <DropdownItem href="/dashboard/student/portfolio" icon={<ClipboardCheck size={18} />} title="Portfolio" text="Présentez vos projets et preuves de compétences." />
              <DropdownItem href={user ? "/dashboard/employer" : "/register?role=employer"} icon={<Building2 size={18} />} title="Espace recruteur" text="Publiez des offres et trouvez des profils qualifiés." />
            </div>
          </DesktopDropdown>
          <Link href="/pricing" className={navLink}>Tarifs</Link>
          <Link href="/about" className={navLink}>À propos</Link>
        </nav>

        <form onSubmit={handleSearch} onFocus={() => setSearchFocused(true)} onBlur={() => window.setTimeout(() => setSearchFocused(false), 120)} className="relative ml-auto hidden w-[280px] shrink-0 2xl:block">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" size={16} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Rechercher partout..."
            autoComplete="off"
            aria-label="Recherche globale"
            className="w-full rounded-xl border border-white/20 bg-white/5 py-2.5 pl-9 pr-3 text-sm text-white outline-none placeholder:text-white/40 focus:border-brand-400 focus:bg-white/10 focus:ring-2 focus:ring-brand-500/20"
          />
          {searchFocused && suggestions.length > 0 && (
            <div className="absolute right-0 top-12 w-[380px] overflow-hidden rounded-2xl border border-slate-200 bg-white p-2 text-ink shadow-soft">
              {suggestions.map((item) => (
                <Link key={`${item.type}-${item.url}`} href={item.url} onMouseDown={(event) => event.preventDefault()} onClick={() => { setSuggestions([]); setSearchFocused(false); }} className="block rounded-xl px-3 py-2.5 hover:bg-slate-50">
                  <span className="block truncate text-sm font-bold text-navy-950">{item.title}</span>
                  <span className="mt-0.5 block truncate text-[11px] text-slate-500">{item.subtitle}</span>
                </Link>
              ))}
              <button type="submit" className="mt-1 w-full rounded-xl bg-brand-50 px-3 py-2 text-left text-xs font-black text-brand-700 hover:bg-brand-100">Voir tous les résultats</button>
            </div>
          )}
        </form>

        <div className="ml-auto flex shrink-0 items-center gap-2 2xl:ml-0">
          <div className="hidden md:block [&_button]:!border-white/20 [&_button]:!bg-white/5 [&_button]:!text-white [&_button:hover]:!bg-white/10">
            <CurrencySelector />
          </div>

          {user && <NotificationBell />}

          <Link href="/cart" className="relative rounded-xl p-2.5 text-white/80 transition hover:bg-white/10 hover:text-white" aria-label="Panier">
            <ShoppingCart size={20} />
            {items.length > 0 && (
              <span className="absolute -right-1 -top-1 grid h-5 w-5 place-items-center rounded-full bg-brand-500 text-[10px] font-black text-white">
                {items.length}
              </span>
            )}
          </Link>

          {!user && (
            <div className="hidden items-center gap-2 sm:flex">
              <Link href="/login" className="btn-dark !whitespace-nowrap !px-4">Se connecter</Link>
              {platform.registration_enabled && <Link href="/register" className="btn-primary !whitespace-nowrap !px-5">S'inscrire</Link>}
            </div>
          )}

          {user && (
            <div ref={profileMenuRef} className="relative hidden sm:block">
              <button onClick={() => setMenuOpen((v) => !v)} className="flex items-center gap-2 rounded-xl border border-white/20 bg-white/5 py-1.5 pl-1.5 pr-2.5 hover:bg-white/10">
                <div className="grid h-8 w-8 place-items-center rounded-lg bg-brand-500 text-sm font-black text-white">
                  {user.first_name?.[0] || user.username[0].toUpperCase()}
                </div>
                <ChevronDown size={15} />
              </button>
              {menuOpen && (
                <div className="absolute right-0 top-12 w-64 rounded-2xl border border-slate-200 bg-white p-2 text-ink shadow-soft">
                  <p className="px-2 py-1 text-sm font-bold">{user.first_name || user.username}</p>
                  <p className="px-2 pb-2 text-xs capitalize text-slate-500">{user.role}</p>
                  <MenuItem href={dashboardHref} icon={<LayoutDashboard size={16} />} label="Tableau de bord" close={() => setMenuOpen(false)} />
                  {user.role !== "employer" && <>
                    <MenuItem href="/dashboard/student" icon={<BookOpen size={16} />} label="Mes cours" close={() => setMenuOpen(false)} />
                    <MenuItem href="/dashboard/student/pdfs" icon={<FileText size={16} />} label="Mes PDF" close={() => setMenuOpen(false)} />
                  </>}
                  {user.role === "student" && <>
                    <MenuItem href="/dashboard/student/projects" icon={<ClipboardCheck size={16} />} label="Mes projets" close={() => setMenuOpen(false)} />
                    <MenuItem href="/dashboard/student/portfolio" icon={<BriefcaseBusiness size={16} />} label="Mon portfolio" close={() => setMenuOpen(false)} />
                    <MenuItem href="/dashboard/student/opportunities" icon={<BriefcaseBusiness size={16} />} label="Emploi & missions" close={() => setMenuOpen(false)} />
                  </>}
                  {user.role === "employer" && <MenuItem href="/dashboard/employer" icon={<Building2 size={16} />} label="Mon entreprise" close={() => setMenuOpen(false)} />}
                  <MenuItem href="/assistant" icon={<Bot size={16} />} label="KalanPro AI" close={() => setMenuOpen(false)} />
                  <MenuItem href="/notifications" icon={<Bell size={16} />} label="Notifications" close={() => setMenuOpen(false)} />
                  <MenuItem href="/dashboard/messages" icon={<MessageCircle size={16} />} label="Messages" close={() => setMenuOpen(false)} />
                  {user.role !== "employer" && <MenuItem href="/dashboard/student/profile" icon={<UserIcon size={16} />} label="Profil" close={() => setMenuOpen(false)} />}
                  {user.role === "admin" && user.technical_admin && (
                    <a href={djangoAdminHref} target="_blank" rel="noreferrer" onClick={() => setMenuOpen(false)} className="flex items-center justify-between gap-2 rounded-lg px-2 py-2 text-sm font-semibold text-brand-700 hover:bg-brand-50">
                      <span className="flex items-center gap-2"><Wrench size={16} /> Administration technique</span><ExternalLink size={13} />
                    </a>
                  )}
                  <button onClick={() => { logout(); setMenuOpen(false); router.push("/"); }} className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-sm text-red-600 hover:bg-red-50">
                    <LogOut size={16} /> Déconnexion
                  </button>
                </div>
              )}
            </div>
          )}

          <button className="rounded-xl p-2.5 text-white hover:bg-white/10 xl:hidden" onClick={() => setMobileOpen((v) => !v)} aria-label="Menu">
            {mobileOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <div className="border-t border-white/10 bg-navy-950 p-4 xl:hidden">
          <form onSubmit={handleSearch} className="relative mb-3">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" size={18} />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Rechercher une compétence..." className="w-full rounded-xl border border-white/20 bg-white/5 py-3 pl-10 pr-4 text-sm text-white outline-none placeholder:text-white/40 focus:border-brand-400" />
          </form>
          <div className="mb-3 md:hidden"><CurrencySelector mobile /></div>
          <div className="grid gap-1">
            <MobileGroup label="Formations">
              <MobileLink href="/courses" label="Cours vidéo" />
              <MobileLink href="/pdfs" label="PDF & Guides" />
              <MobileLink href="/formations" label="Cohortes live" />
              <MobileLink href="/courses?domain=technologie-numerique" label="Domaines" />
            </MobileGroup>
            <MobileGroup label="Mentorat">
              <MobileLink href="/mentorship" label="Trouver un mentor" />
              <MobileLink href="/become-instructor" label="Devenir instructeur" />
            </MobileGroup>
            <MobileGroup label="Opportunités">
              <MobileLink href="/opportunities" label="Emplois & missions" />
              <MobileLink href={user ? "/dashboard/employer" : "/register?role=employer"} label="Espace recruteur" />
            </MobileGroup>
            <MobileLink href="/instructors" label="Instructeurs" />
            <MobileLink href="/pricing" label="Tarifs" />
            <MobileLink href="/about" label="À propos" />
            {!user ? (
              <div className="mt-3 grid grid-cols-2 gap-2">
                <Link href="/login" className="btn-dark">Se connecter</Link>
                {platform.registration_enabled && <Link href="/register" className="btn-primary">S'inscrire</Link>}
              </div>
            ) : (
              <>
                <Link href={dashboardHref} className="mt-2 rounded-xl bg-brand-500 px-3 py-3 text-sm font-bold text-white">Tableau de bord</Link>
                <MobileLink href="/assistant" label="KalanPro AI" />
                <MobileLink href="/notifications" label="Notifications" />
                {user.role === "employer" && <MobileLink href="/dashboard/employer" label="Mon entreprise" />}
              </>
            )}
          </div>
        </div>
      )}
    </header>
  );
}

function MenuItem({ href, icon, label, close }: { href: string; icon: React.ReactNode; label: string; close: () => void }) {
  return <Link href={href} onClick={close} className="flex items-center gap-2 rounded-lg px-2 py-2 text-sm hover:bg-slate-50">{icon}{label}</Link>;
}

function MobileLink({ href, label }: { href: string; label: string }) {
  return <Link href={href} className="rounded-xl px-3 py-2.5 text-sm font-semibold text-white/80 hover:bg-white/10 hover:text-white">{label}</Link>;
}

function DesktopDropdown({ label, href, linkClass, width, children }: { label: string; href: string; linkClass: string; width: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    function closeOutside(event: MouseEvent) {
      if (open && rootRef.current && !rootRef.current.contains(event.target as Node)) setOpen(false);
    }
    function closeEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        (rootRef.current?.querySelector("a") as HTMLElement | null)?.blur();
      }
    }
    document.addEventListener("mousedown", closeOutside);
    document.addEventListener("keydown", closeEscape);
    return () => {
      document.removeEventListener("mousedown", closeOutside);
      document.removeEventListener("keydown", closeEscape);
    };
  }, [open]);

  function closeFromSelection(event: React.MouseEvent<HTMLDivElement>) {
    if ((event.target as HTMLElement).closest("a")) setOpen(false);
  }

  return (
    <div
      ref={rootRef}
      className="relative"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
      onFocus={() => setOpen(true)}
      onBlur={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) setOpen(false);
      }}
    >
      <Link href={href} onClick={() => setOpen(false)} className={`${linkClass} flex items-center gap-1.5`} aria-expanded={open}>
        {label}<ChevronDown size={14} className={`transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
      </Link>
      <div
        onClick={closeFromSelection}
        className={`absolute left-0 top-full z-[70] pt-3 transition duration-150 ${
          open
            ? "pointer-events-auto visible translate-y-0 opacity-100"
            : "pointer-events-none invisible translate-y-1 opacity-0"
        }`}
      >
        <div className={`${width} overflow-hidden rounded-2xl border border-slate-200 bg-white text-navy-950 shadow-[0_24px_70px_rgba(3,15,38,.24)]`}>
          {children}
        </div>
      </div>
    </div>
  );
}

function DropdownItem({ href, icon, title, text }: { href: string; icon: React.ReactNode; title: string; text: string }) {
  return (
    <Link href={href} className="group/item flex gap-3 rounded-xl p-3 transition hover:bg-brand-50">
      <span className="mt-0.5 grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-navy-50 text-navy-800 transition group-hover/item:bg-brand-500 group-hover/item:text-white">{icon}</span>
      <span className="min-w-0"><span className="block text-sm font-black text-navy-950">{title}</span><span className="mt-0.5 block text-xs leading-5 text-slate-500">{text}</span></span>
    </Link>
  );
}

function DomainLink({ href, label }: { href: string; label: string }) {
  return <Link href={href} className="rounded-lg px-2.5 py-2 text-sm font-semibold text-slate-600 transition hover:bg-white hover:text-brand-600 hover:shadow-sm">{label}</Link>;
}

function MobileGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <details className="group/mobile rounded-xl">
      <summary className="flex cursor-pointer list-none items-center justify-between rounded-xl px-3 py-2.5 text-sm font-semibold text-white/80 hover:bg-white/10 hover:text-white">
        {label}<ChevronDown size={15} className="transition group-open/mobile:rotate-180" />
      </summary>
      <div className="ml-3 grid border-l border-white/10 pl-2">{children}</div>
    </details>
  );
}
