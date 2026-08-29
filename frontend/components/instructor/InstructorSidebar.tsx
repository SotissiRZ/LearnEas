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
  { href: "/dashboard/instructor/formations", label: "Formations live", icon: Video },
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
    <aside className="lg:sticky lg:top-20 lg:self-start">
      <div className="card overflow-hidden">
        <div className="border-b border-gray-100 px-4 py-4">
          <div className="flex items-center gap-2 font-bold text-ink">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-brand-50 text-brand-700">
              <GraduationCap size={18} />
            </span>
            <div>
              <p className="text-sm">Espace instructeur</p>
              <p className="text-[11px] font-normal text-gray-400">Création, suivi et revenus</p>
            </div>
          </div>
        </div>
        <nav className="flex gap-1 overflow-x-auto p-2 lg:flex-col lg:overflow-visible" aria-label="Espace instructeur">
          {ITEMS.map(({ href, label, icon: Icon, exact = false }) => {
            const active = exact ? pathname === href : pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                href={href}
                className={`flex shrink-0 items-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                  active ? "bg-brand-50 text-brand-700" : "text-gray-600 hover:bg-gray-50 hover:text-ink"
                }`}
              >
                <Icon size={17} />
                {label}
              </Link>
            );
          })}
        </nav>
      </div>
    </aside>
  );
}
