import { levelLabel } from "@/lib/api";

const COLORS: Record<string, string> = {
  beginner: "bg-emerald-50 text-emerald-700",
  intermediate: "bg-amber-50 text-amber-700",
  expert: "bg-rose-50 text-rose-700",
};

export default function LevelBadge({ level }: { level: string }) {
  return <span className={`badge ${COLORS[level] || "bg-gray-100 text-gray-700"}`}>{levelLabel(level)}</span>;
}
