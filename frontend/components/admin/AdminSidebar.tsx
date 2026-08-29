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
  { tab: "categories", label: "Catégories", icon: Tags },
  { tab: "moderation", label: "FAQ & avis", icon: MessageSquareText },
  { tab: "settings", label: "Paramètres", icon: Settings },
] as const;

export type AdminTab = (typeof ITEMS)[number]["tab"];

export default function AdminSidebar({ activeTab }: { activeTab: AdminTab }) {
  return (
    <aside className="lg:sticky lg:top-20 lg:self-start">
      <div className="card overflow-hidden">
        <div className="border-b border-gray-100 px-4 py-4">
          <div className="flex items-center gap-2 font-bold text-ink">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-brand-50 text-brand-700">
              <ShieldCheck size={18} />
            </span>
            <div>
              <p className="text-sm">Administration</p>
              <p className="text-[11px] font-normal text-gray-400">Back-office LearnEas</p>
            </div>
          </div>
        </div>
        <nav className="flex gap-1 overflow-x-auto p-2 lg:flex-col lg:overflow-visible" aria-label="Administration">
          {ITEMS.map(({ tab, label, icon: Icon }) => (
            <Link
              key={tab}
              href={tab === "overview" ? "/dashboard/admin" : `/dashboard/admin?tab=${tab}`}
              className={`flex shrink-0 items-center gap-2 rounded-lg px-3 py-2.5 text-sm font-medium transition ${
                activeTab === tab
                  ? "bg-brand-50 text-brand-700"
                  : "text-gray-600 hover:bg-gray-50 hover:text-ink"
              }`}
            >
              <Icon size={17} />
              {label}
            </Link>
          ))}
        </nav>
      </div>
    </aside>
  );
}
