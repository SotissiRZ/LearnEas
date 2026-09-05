"use client";

import dynamic from "next/dynamic";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Loader2, Sparkles } from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

const Assistant = dynamic(() => import("@/components/ai/KalanProAssistant"), {
  ssr: false,
  loading: () => (
    <button
      type="button"
      disabled
      className="fixed bottom-[max(5.5rem,env(safe-area-inset-bottom))] right-[max(1rem,env(safe-area-inset-right))] z-[70] flex items-center gap-2 rounded-full bg-gradient-to-r from-brand-500 to-orange-400 px-4 py-3 text-sm font-black text-white shadow-[0_15px_45px_rgba(255,100,26,.35)] sm:right-[max(1.5rem,env(safe-area-inset-right))]"
      aria-label="Chargement de KalanPro AI"
    >
      <Loader2 size={17} className="animate-spin" /> KalanPro AI
    </button>
  ),
});

function preloadAssistant() {
  void import("@/components/ai/KalanProAssistant");
}

/**
 * Launcher ultra-léger : les ~centaines de lignes de l'espace IA ne sont téléchargées et
 * hydratées qu'au moment où l'utilisateur en a réellement besoin. Cela réduit fortement le
 * travail JavaScript sur chaque page et améliore la réactivité des premières navigations.
 */
export default function LazyKalanProAssistant() {
  const pathname = usePathname();
  const hydrated = useAuth((state) => state.hydrated);
  const user = useAuth((state) => state.user);
  const [activated, setActivated] = useState(false);

  if (!hydrated || pathname.startsWith("/live/session/") || pathname === "/assistant") return null;
  if (activated) return <Assistant initialOpen />;

  return (
    <button
      type="button"
      onPointerEnter={preloadAssistant}
      onFocus={preloadAssistant}
      onClick={() => setActivated(true)}
      className="fixed bottom-[max(5.5rem,env(safe-area-inset-bottom))] right-[max(1rem,env(safe-area-inset-right))] z-[70] flex items-center gap-2 rounded-full bg-gradient-to-r from-brand-500 to-orange-400 px-4 py-3 text-sm font-black text-white shadow-[0_15px_45px_rgba(255,100,26,.35)] transition hover:shadow-[0_18px_50px_rgba(255,100,26,.42)] sm:right-[max(1.5rem,env(safe-area-inset-right))]"
      aria-label="Ouvrir KalanPro AI"
      title="KalanPro AI"
    >
      <Sparkles size={17} />
      <span className={pathname === "/" ? "inline" : "hidden sm:inline"}>{user ? "KalanPro AI" : "Essayer KalanPro AI"}</span>
    </button>
  );
}
