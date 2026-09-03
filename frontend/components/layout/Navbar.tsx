"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import {
  Search, ShoppingCart, GraduationCap, ChevronDown, LayoutDashboard,
  BookOpen, FileText, LogOut, User as UserIcon, Menu, X, MessageCircle, Wrench, ExternalLink,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useCart } from "@/hooks/useCart";
import { api } from "@/lib/api";
import CurrencySelector from "@/components/layout/CurrencySelector";

export default function Navbar() {
  const router = useRouter();
  const pathname = usePathname();
  const { user, logout } = useAuth();
  const items = useCart((s) => s.items);
  const [query, setQuery] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [platform, setPlatform] = useState({ site_name: "LearnEas", registration_enabled: true });
  const profileMenuRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    setMenuOpen(false);
    setMobileOpen(false);
  }, [pathname]);

  useEffect(() => {
    api.get<{ site_name: string; registration_enabled: boolean }>("/auth/platform-settings/")
      .then((data) => setPlatform({ site_name: data.site_name || "LearnEas", registration_enabled: data.registration_enabled }))
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    function closeOutside(event: MouseEvent) {
      if (menuOpen && profileMenuRef.current && !profileMenuRef.current.contains(event.target as Node)) {
        setMenuOpen(false);
      }
    }
    function closeEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setMenuOpen(false);
    }
    document.addEventListener("mousedown", closeOutside);
    document.addEventListener("keydown", closeEscape);
    return () => {
      document.removeEventListener("mousedown", closeOutside);
      document.removeEventListener("keydown", closeEscape);
    };
  }, [menuOpen]);

  function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    router.push(`/courses?search=${encodeURIComponent(query)}`);
  }

  const dashboardHref =
    user?.role === "admin" ? "/dashboard/admin" : user?.role === "instructor" ? "/dashboard/instructor" : "/dashboard/student";
  const djangoAdminHref = (process.env.NEXT_PUBLIC_API_URL || "/api").replace(/\/api\/?$/, "/admin/");

  return (
    <header className="fixed inset-x-0 top-0 z-50 border-b border-gray-100 bg-white/95 shadow-sm backdrop-blur">
      <div className="container-app flex h-16 items-center gap-4">
        <Link href="/" className="flex items-center gap-2 shrink-0">
          <div className="grid h-9 w-9 place-items-center rounded-xl bg-brand-600 text-white">
            <GraduationCap size={20} />
          </div>
          <span className="text-lg font-extrabold tracking-tight">
            {platform.site_name === "LearnEas" ? <>Learn<span className="text-brand-600">Eas</span></> : platform.site_name}
          </span>
        </Link>

        <nav className="hidden items-center gap-1 lg:flex">
          <Link href="/courses" className="btn-ghost !px-3">Cours</Link>
          <Link href="/formations" className="btn-ghost !px-3">Formations interactives</Link>
          <Link href="/pdfs" className="btn-ghost !px-3">PDF & Guides</Link>
          <Link href="/instructors" className="btn-ghost !px-3">Instructeurs</Link>
        </nav>

        <form onSubmit={handleSearch} className="relative mx-auto hidden max-w-md flex-1 md:block">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Rechercher un cours, un PDF, une compétence..."
            className="w-full rounded-full border border-gray-200 bg-gray-50 py-2.5 pl-10 pr-4 text-sm outline-none focus:border-brand-500 focus:bg-white focus:ring-2 focus:ring-brand-100"
          />
        </form>

        <div className="ml-auto flex items-center gap-2">
          <CurrencySelector />

          <Link href="/cart" className="relative rounded-full p-2 hover:bg-gray-100">
            <ShoppingCart size={22} />
            {items.length > 0 && (
              <span className="absolute -right-1 -top-1 grid h-5 w-5 place-items-center rounded-full bg-brand-600 text-[11px] font-bold text-white">
                {items.length}
              </span>
            )}
          </Link>

          {!user && (
            <div className="hidden items-center gap-2 sm:flex">
              <Link href="/login" className="btn-ghost">Connexion</Link>
              {platform.registration_enabled && <Link href="/register" className="btn-primary">S'inscrire</Link>}
            </div>
          )}

          {user && (
            <div ref={profileMenuRef} className="relative hidden sm:block">
              <button
                onClick={() => setMenuOpen((v) => !v)}
                className="flex items-center gap-2 rounded-full border border-gray-200 py-1 pl-1 pr-2 hover:bg-gray-50"
              >
                <div className="grid h-8 w-8 place-items-center rounded-full bg-brand-100 text-sm font-bold text-brand-700">
                  {user.first_name?.[0] || user.username[0].toUpperCase()}
                </div>
                <ChevronDown size={16} />
              </button>
              {menuOpen && (
                <div className="absolute right-0 top-12 w-64 rounded-xl border border-gray-100 bg-white p-2 shadow-soft">
                  <p className="px-2 py-1 text-sm font-semibold">{user.first_name || user.username}</p>
                  <p className="px-2 pb-2 text-xs capitalize text-gray-500">{user.role}</p>
                  <Link href={dashboardHref} onClick={() => setMenuOpen(false)} className="flex items-center gap-2 rounded-lg px-2 py-2 text-sm hover:bg-gray-50">
                    <LayoutDashboard size={16} /> Tableau de bord
                  </Link>
                  <Link href="/dashboard/student" onClick={() => setMenuOpen(false)} className="flex items-center gap-2 rounded-lg px-2 py-2 text-sm hover:bg-gray-50">
                    <BookOpen size={16} /> Mes cours
                  </Link>
                  <Link href="/dashboard/student/pdfs" onClick={() => setMenuOpen(false)} className="flex items-center gap-2 rounded-lg px-2 py-2 text-sm hover:bg-gray-50">
                    <FileText size={16} /> Mes PDF
                  </Link>
                  <Link href="/dashboard/messages" onClick={() => setMenuOpen(false)} className="flex items-center gap-2 rounded-lg px-2 py-2 text-sm hover:bg-gray-50">
                    <MessageCircle size={16} /> Messages
                  </Link>
                  <Link href="/dashboard/student/profile" onClick={() => setMenuOpen(false)} className="flex items-center gap-2 rounded-lg px-2 py-2 text-sm hover:bg-gray-50">
                    <UserIcon size={16} /> Profil
                  </Link>
                  {user.role === "admin" && user.technical_admin && (
                    <a
                      href={djangoAdminHref}
                      target="_blank"
                      rel="noreferrer"
                      onClick={() => setMenuOpen(false)}
                      className="flex items-center justify-between gap-2 rounded-lg px-2 py-2 text-sm font-semibold text-brand-700 hover:bg-brand-50"
                    >
                      <span className="flex items-center gap-2"><Wrench size={16} /> Administration technique</span>
                      <ExternalLink size={13} />
                    </a>
                  )}
                  <button
                    onClick={() => { logout(); setMenuOpen(false); router.push("/"); }}
                    className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left text-sm text-red-600 hover:bg-red-50"
                  >
                    <LogOut size={16} /> Déconnexion
                  </button>
                </div>
              )}
            </div>
          )}

          <button className="rounded-full p-2 hover:bg-gray-100 lg:hidden" onClick={() => setMobileOpen((v) => !v)}>
            {mobileOpen ? <X size={22} /> : <Menu size={22} />}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <div className="border-t border-gray-100 bg-white p-4 lg:hidden">
          <form onSubmit={handleSearch} className="relative mb-3">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Rechercher..."
              className="w-full rounded-full border border-gray-200 bg-gray-50 py-2.5 pl-10 pr-4 text-sm"
            />
          </form>
          <div className="flex flex-col gap-1">
            <div className="mb-2"><CurrencySelector mobile /></div>
            <Link href="/courses" className="rounded-lg px-3 py-2 hover:bg-gray-50">Cours</Link>
            <Link href="/formations" className="rounded-lg px-3 py-2 hover:bg-gray-50">Formations interactives</Link>
            <Link href="/pdfs" className="rounded-lg px-3 py-2 hover:bg-gray-50">PDF & Guides</Link>
            <Link href="/instructors" className="rounded-lg px-3 py-2 hover:bg-gray-50">Instructeurs</Link>
            {!user ? (
              <>
                <Link href="/login" className="rounded-lg px-3 py-2 hover:bg-gray-50">Connexion</Link>
                {platform.registration_enabled && <Link href="/register" className="rounded-lg px-3 py-2 font-semibold text-brand-700">S'inscrire</Link>}
              </>
            ) : (
              <>
                <Link
                  href={dashboardHref}
                  onClick={() => setMobileOpen(false)}
                  className="rounded-lg px-3 py-2 font-semibold text-brand-700"
                >
                  Tableau de bord
                </Link>
                {user.role === "admin" && user.technical_admin && (
                  <a
                    href={djangoAdminHref}
                    target="_blank"
                    rel="noreferrer"
                    onClick={() => setMobileOpen(false)}
                    className="flex items-center gap-2 rounded-lg px-3 py-2 font-semibold text-brand-700 hover:bg-brand-50"
                  >
                    <Wrench size={16} /> Administration technique <ExternalLink size={13} />
                  </a>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
