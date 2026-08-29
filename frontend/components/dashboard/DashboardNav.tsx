"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, BookOpen, FileText, User, PlusCircle, Users, ShoppingBag, Video, Award } from "lucide-react";

const LINKS: Record<string, { href: string; label: string; icon: React.ReactNode }[]> = {
  student: [
    { href: "/dashboard/student", label: "Mes cours", icon: <BookOpen size={16} /> },
    { href: "/dashboard/student/formations", label: "Mes formations", icon: <Video size={16} /> },
    { href: "/dashboard/student/pdfs", label: "Mes PDF", icon: <FileText size={16} /> },
    { href: "/dashboard/student/certificates", label: "Mes certificats", icon: <Award size={16} /> },
    { href: "/dashboard/student/profile", label: "Profil", icon: <User size={16} /> },
  ],
  instructor: [
    { href: "/dashboard/instructor", label: "Aperçu", icon: <LayoutDashboard size={16} /> },
    { href: "/dashboard/instructor/courses", label: "Mes cours", icon: <BookOpen size={16} /> },
    { href: "/dashboard/instructor/courses/new", label: "Nouveau cours", icon: <PlusCircle size={16} /> },
    { href: "/dashboard/instructor/formations", label: "Formations interactives", icon: <Video size={16} /> },
    { href: "/dashboard/instructor/formations/new", label: "Nouvelle formation", icon: <PlusCircle size={16} /> },
    { href: "/dashboard/instructor/pdfs", label: "Mes PDF", icon: <FileText size={16} /> },
    { href: "/dashboard/instructor/pdfs/new", label: "Nouveau PDF", icon: <PlusCircle size={16} /> },
  ],
  admin: [
    { href: "/dashboard/admin", label: "Aperçu", icon: <LayoutDashboard size={16} /> },
    { href: "/dashboard/admin?tab=users", label: "Utilisateurs", icon: <Users size={16} /> },
    { href: "/dashboard/admin?tab=orders", label: "Commandes", icon: <ShoppingBag size={16} /> },
  ],
};

export default function DashboardNav({ role }: { role: "student" | "instructor" | "admin" }) {
  const pathname = usePathname();
  const links = LINKS[role];

  return (
    <div className="mb-8 flex flex-wrap gap-2 border-b border-gray-100 pb-4">
      {links.map((l) => (
        <Link
          key={l.href}
          href={l.href}
          className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium ${
            pathname === l.href.split("?")[0] ? "bg-brand-50 text-brand-700" : "text-gray-600 hover:bg-gray-50"
          }`}
        >
          {l.icon} {l.label}
        </Link>
      ))}
    </div>
  );
}
