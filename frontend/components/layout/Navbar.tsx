"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import {
  Search, ShoppingCart, ChevronDown, LayoutDashboard, BookOpen, FileText, LogOut,
  User as UserIcon, Menu, X, MessageCircle, Wrench, ExternalLink, ClipboardCheck,
  BriefcaseBusiness,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useCart } from "@/hooks/useCart";
import { api } from "@/lib/api";
import CurrencySelector from "@/components/layout/CurrencySelector";
import BrandLogo from "@/components/layout/BrandLogo";

export default function Navbar() {
  const router = useRouter();
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const items = useCart((s) => s.items);
  const [query, setQuery] = useState("");
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
    router.push(term ? `/courses?search=${encodeURIComponent(term)}` : "/courses");
  }

  const dashboardHref = user?.role === "admin" ? "/dashboard/admin" : user?.role === "instructor" ? "/dashboard/instructor" : "/dashboard/student";
  const djangoAdminHref = (process.env.NEXT_PUBLIC_API_URL || "/api").replace(/\/api\/?$/, "/admin/");
  const navLink = "rounded-lg px-3 py-2 text-sm font-semibold text-white/80 transition hover:bg-white/10 hover:text-white";

  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-white/10 bg-navy-950/95 text-white shadow-[0_8px_30px_rgba(6,21,47,.18)] backdrop-blur-xl">
      <div className="container-app flex h-[72px] items-center gap-3">
        <BrandLogo />

        <nav className="ml-5 hidden items-center gap-1 lg:flex" aria-label="Navigation principale">
          <Link href="/courses" className={navLink}>Formations</Link>
          <Link href="/mentorship" className={navLink}>Mentorat</Link>
          <Link href="/opportunities" className={navLink}>Opportunités</Link>
          <Link href="/about" className={navLink}>À propos</Link>
        </nav>

        <form onSubmit={handleSearch} className="relative ml-auto hidden w-full max-w-[250px] xl:block">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" size={16} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Rechercher..."
            className="w-full rounded-xl border border-white/20 bg-white/5 py-2.5 pl-9 pr-3 text-sm text-white outline-none placeholder:text-white/40 focus:border-brand-400 focus:bg-white/10 focus:ring-2 focus:ring-brand-500/20"
          />
        </form>

        <div className="ml-auto flex items-center gap-1.5 xl:ml-0">
          <div className="hidden md:block [&_button]:!border-white/20 [&_button]:!bg-white/5 [&_button]:!text-white [&_button:hover]:!bg-white/10">
            <CurrencySelector />
          </div>

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
              <Link href="/login" className="btn-dark !px-4">Se connecter</Link>
              {platform.registration_enabled && <Link href="/register" className="btn-primary !px-5">S'inscrire</Link>}
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
                  <MenuItem href="/dashboard/student" icon={<BookOpen size={16} />} label="Mes cours" close={() => setMenuOpen(false)} />
                  <MenuItem href="/dashboard/student/pdfs" icon={<FileText size={16} />} label="Mes PDF" close={() => setMenuOpen(false)} />
                  {user.role === "student" && <>
                    <MenuItem href="/dashboard/student/projects" icon={<ClipboardCheck size={16} />} label="Mes projets" close={() => setMenuOpen(false)} />
                    <MenuItem href="/dashboard/student/portfolio" icon={<BriefcaseBusiness size={16} />} label="Mon portfolio" close={() => setMenuOpen(false)} />
                  </>}
                  <MenuItem href="/dashboard/student/opportunities" icon={<BriefcaseBusiness size={16} />} label="Emploi & missions" close={() => setMenuOpen(false)} />
                  <MenuItem href="/dashboard/employer" icon={<UserIcon size={16} />} label="Espace recruteur" close={() => setMenuOpen(false)} />
                  <MenuItem href="/dashboard/messages" icon={<MessageCircle size={16} />} label="Messages" close={() => setMenuOpen(false)} />
                  <MenuItem href="/dashboard/student/profile" icon={<UserIcon size={16} />} label="Profil" close={() => setMenuOpen(false)} />
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

          <button className="rounded-xl p-2.5 text-white hover:bg-white/10 lg:hidden" onClick={() => setMobileOpen((v) => !v)} aria-label="Menu">
            {mobileOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <div className="border-t border-white/10 bg-navy-950 p-4 lg:hidden">
          <form onSubmit={handleSearch} className="relative mb-3">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" size={18} />
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Rechercher une compétence..." className="w-full rounded-xl border border-white/20 bg-white/5 py-3 pl-10 pr-4 text-sm text-white outline-none placeholder:text-white/40 focus:border-brand-400" />
          </form>
          <div className="mb-3 md:hidden"><CurrencySelector mobile /></div>
          <div className="grid gap-1">
            <MobileLink href="/courses" label="Formations" />
            <MobileLink href="/formations" label="Cohortes live" />
            <MobileLink href="/mentorship" label="Mentorat" />
            <MobileLink href="/opportunities" label="Opportunités" />
            <MobileLink href="/pdfs" label="PDF & Guides" />
            <MobileLink href="/instructors" label="Instructeurs" />
            <MobileLink href="/about" label="À propos" />
            {!user ? (
              <div className="mt-3 grid grid-cols-2 gap-2">
                <Link href="/login" className="btn-dark">Se connecter</Link>
                {platform.registration_enabled && <Link href="/register" className="btn-primary">S'inscrire</Link>}
              </div>
            ) : (
              <>
                <Link href={dashboardHref} className="mt-2 rounded-xl bg-brand-500 px-3 py-3 text-sm font-bold text-white">Tableau de bord</Link>
                <MobileLink href="/dashboard/employer" label="Espace recruteur" />
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
