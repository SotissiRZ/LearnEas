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
    hydrateAuth();
    hydrateCart();
    hydrateCurrency();
  }, [hydrateAuth, hydrateCart, hydrateCurrency]);

  return null;
}
