"use client";

import { useEffect } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useCart } from "@/hooks/useCart";
import { useCurrency } from "@/hooks/useCurrency";

export default function AppHydrator() {
  const hydrateAuth = useAuth((s) => s.hydrate);
  const hydrateCart = useCart((s) => s.hydrate);
  const hydrateCurrency = useCurrency((s) => s.hydrate);

  useEffect(() => {
    const expire = () => useAuth.setState({ user: null, hydrated: true });
    window.addEventListener("learneas:auth-expired", expire);

    // L'authentification et le panier sont nécessaires immédiatement. Les devises sont
    // décoratives au premier rendu : les charger pendant un temps idle évite de concurrencer
    // la restauration de session et la première navigation avec une requête réseau non critique.
    void hydrateAuth();
    hydrateCart();

    let timeoutId: number | undefined;
    let idleId: number | undefined;
    const idleWindow = window as Window & {
      requestIdleCallback?: (cb: () => void, opts?: { timeout: number }) => number;
      cancelIdleCallback?: (id: number) => void;
    };
    const runCurrencyHydration = () => { void hydrateCurrency(); };
    if (typeof idleWindow.requestIdleCallback === "function") {
      idleId = idleWindow.requestIdleCallback(runCurrencyHydration, { timeout: 1500 });
    } else {
      timeoutId = window.setTimeout(runCurrencyHydration, 350);
    }

    return () => {
      window.removeEventListener("learneas:auth-expired", expire);
      if (timeoutId !== undefined) window.clearTimeout(timeoutId);
      if (idleId !== undefined && typeof idleWindow.cancelIdleCallback === "function") {
        idleWindow.cancelIdleCallback(idleId);
      }
    };
  }, [hydrateAuth, hydrateCart, hydrateCurrency]);

  return null;
}
