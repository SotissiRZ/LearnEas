"use client";

import Link from "next/link";
import {
  LayoutDashboard,
  Users,
  UserCheck,
  Library,
  ShoppingBag,
  WalletCards,
  Video,
  Tags,
  Settings,
  ShieldCheck,
  MessageSquareText,
  Award,
  BriefcaseBusiness,
} from "lucide-react";

const ITEMS = [
  { tab: "overview", label: "Aperçu", icon: LayoutDashboard },
  { tab: "users", label: "Utilisateurs", icon: Users },
  { tab: "applications", label: "Demandes instructeur", icon: UserCheck },
  { tab: "content", label: "Contenus", icon: Library },
  { tab: "orders", label: "Commandes", icon: ShoppingBag },
  { tab: "payouts", label: "Versements", icon: WalletCards },
  { tab: "sessions", label: "Séances live", icon: Video },
  { tab: "certificates", label: "Certificats", icon: Award },
  { tab: "recruitment", label: "Recrutement", icon: BriefcaseBusiness },
  { tab: "categories", label: "Catégories", icon: Tags },
  { tab: "moderation", label: "FAQ & avis", icon: MessageSquareText },
  { tab: "settings", label: "Paramètres", icon: Settings },
] as const;

export type AdminTab = (typeof ITEMS)[number]["tab"];

export default function AdminSidebar({ activeTab }: { activeTab: AdminTab }) {
  return (
    <aside className="peer group sticky top-16 z-30 self-start bg-white py-2 lg:absolute lg:inset-y-0 lg:left-0 lg:top-0 lg:z-50 lg:h-full lg:w-16 lg:overflow-hidden lg:bg-white lg:py-0 lg:shadow-sm lg:transition-[width] lg:duration-200 lg:ease-out lg:hover:w-60">
      <div className="card overflow-hidden lg:flex lg:h-full lg:min-h-0 lg:flex-col lg:rounded-none lg:border-y-0 lg:border-l-0 lg:border-r lg:border-gray-200 lg:shadow-none">
        <div className="border-b border-gray-100 px-4 py-4 lg:flex lg:h-[70px] lg:shrink-0 lg:items-center lg:px-3">
          <div className="flex items-center gap-3 font-bold text-ink lg:w-full lg:min-w-0">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-brand-50 text-brand-700 lg:mx-auto lg:transition-all lg:duration-200 lg:group-hover:mx-0">
              <ShieldCheck size={18} />
            </span>
            <div className="min-w-0 lg:max-w-0 lg:overflow-hidden lg:whitespace-nowrap lg:opacity-0 lg:transition-all lg:duration-200 lg:group-hover:max-w-[170px] lg:group-hover:opacity-100">
              <p className="text-sm">Administration</p>
              <p className="text-[11px] font-normal text-gray-400">Back-office LearnEas</p>
            </div>
          </div>
        </div>

        <nav className="flex gap-1 overflow-x-auto p-2 lg:min-h-0 lg:flex-1 lg:flex-col lg:overflow-x-hidden lg:overflow-y-auto lg:overscroll-contain lg:px-2 lg:py-3" aria-label="Administration">
          {ITEMS.map(({ tab, label, icon: Icon }) => (
            <Link
              key={tab}
              href={tab === "overview" ? "/dashboard/admin" : `/dashboard/admin?tab=${tab}`}
              title={label}
              className={`flex shrink-0 items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors lg:h-10 lg:w-full lg:justify-center lg:px-0 lg:group-hover:justify-start lg:group-hover:px-3 ${
                activeTab === tab
                  ? "bg-brand-50 text-brand-700"
                  : "text-gray-600 hover:bg-gray-50 hover:text-ink"
              }`}
            >
              <Icon size={18} className="shrink-0" />
              <span className="whitespace-nowrap lg:max-w-0 lg:overflow-hidden lg:opacity-0 lg:transition-all lg:duration-200 lg:group-hover:max-w-[170px] lg:group-hover:opacity-100">
                {label}
              </span>
            </Link>
          ))}
        </nav>
      </div>
    </aside>
  );
}
