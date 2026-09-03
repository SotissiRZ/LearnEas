"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  BookOpen,
  FileText,
  Video,
  Users,
  BarChart3,
  Star,
  WalletCards,
  MessagesSquare,
  UserRoundCog,
  GraduationCap,
  Award,
  CalendarCheck2,
  ClipboardCheck,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

type InstructorNavItem = {
  href: string;
  label: string;
  icon: LucideIcon;
  exact?: boolean;
};

const ITEMS: readonly InstructorNavItem[] = [
  { href: "/dashboard/instructor", label: "Aperçu", icon: LayoutDashboard, exact: true },
  { href: "/dashboard/instructor/courses", label: "Mes cours", icon: BookOpen },
  { href: "/dashboard/instructor/pdfs", label: "Mes PDF", icon: FileText },
  { href: "/dashboard/instructor/formations", label: "Cohortes live", icon: Video },
  { href: "/dashboard/instructor/mentorship", label: "Mentorat 1:1", icon: CalendarCheck2 },
  { href: "/dashboard/instructor/projects", label: "Projets & corrections", icon: ClipboardCheck },
  { href: "/dashboard/instructor/sessions", label: "Séances live", icon: GraduationCap },
  { href: "/dashboard/instructor/students", label: "Étudiants", icon: Users },
  { href: "/dashboard/instructor/analytics", label: "Statistiques", icon: BarChart3 },
  { href: "/dashboard/instructor/reviews", label: "Avis & questions", icon: Star },
  { href: "/dashboard/instructor/certificates", label: "Certificats", icon: Award },
  { href: "/dashboard/instructor/finance", label: "Revenus & versements", icon: WalletCards },
  { href: "/dashboard/instructor/messages", label: "Messages", icon: MessagesSquare },
  { href: "/dashboard/instructor/profile", label: "Profil & paramètres", icon: UserRoundCog },
];

export default function InstructorSidebar() {
  const pathname = usePathname();

  return (
    <aside className="peer group sticky top-16 z-30 self-start bg-white py-2 lg:absolute lg:inset-y-0 lg:left-0 lg:top-0 lg:z-50 lg:h-full lg:w-16 lg:overflow-hidden lg:bg-white lg:py-0 lg:shadow-sm lg:transition-[width] lg:duration-200 lg:ease-out lg:hover:w-60">
      <div className="card overflow-hidden lg:flex lg:h-full lg:min-h-0 lg:flex-col lg:rounded-none lg:border-y-0 lg:border-l-0 lg:border-r lg:border-gray-200 lg:shadow-none">
        <div className="border-b border-gray-100 px-4 py-4 lg:flex lg:h-[70px] lg:shrink-0 lg:items-center lg:px-3">
          <div className="flex items-center gap-3 font-bold text-ink lg:w-full lg:min-w-0">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-brand-50 text-brand-700 lg:mx-auto lg:transition-all lg:duration-200 lg:group-hover:mx-0">
              <GraduationCap size={18} />
            </span>
            <div className="min-w-0 lg:max-w-0 lg:overflow-hidden lg:whitespace-nowrap lg:opacity-0 lg:transition-all lg:duration-200 lg:group-hover:max-w-[170px] lg:group-hover:opacity-100">
              <p className="text-sm">Espace instructeur</p>
              <p className="text-[11px] font-normal text-gray-400">Création, suivi et revenus</p>
            </div>
          </div>
        </div>

        <nav className="flex gap-1 overflow-x-auto p-2 lg:min-h-0 lg:flex-1 lg:flex-col lg:overflow-x-hidden lg:overflow-y-auto lg:overscroll-contain lg:px-2 lg:py-3" aria-label="Espace instructeur">
          {ITEMS.map(({ href, label, icon: Icon, exact = false }) => {
            const active = exact ? pathname === href : pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                href={href}
                title={label}
                className={`flex shrink-0 items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors lg:h-10 lg:w-full lg:justify-center lg:px-0 lg:group-hover:justify-start lg:group-hover:px-3 ${
                  active ? "bg-brand-50 text-brand-700" : "text-gray-600 hover:bg-gray-50 hover:text-ink"
                }`}
              >
                <Icon size={18} className="shrink-0" />
                <span className="whitespace-nowrap lg:max-w-0 lg:overflow-hidden lg:opacity-0 lg:transition-all lg:duration-200 lg:group-hover:max-w-[170px] lg:group-hover:opacity-100">
                  {label}
                </span>
              </Link>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}
