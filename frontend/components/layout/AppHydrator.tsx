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
    void hydrateAuth();
    hydrateCart();
    hydrateCurrency();
    return () => window.removeEventListener("learneas:auth-expired", expire);
  }, [hydrateAuth, hydrateCart, hydrateCurrency]);

  return null;
}
