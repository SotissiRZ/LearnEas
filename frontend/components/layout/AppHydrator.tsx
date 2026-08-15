"use client";

import { useEffect } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useCart } from "@/hooks/useCart";

export default function AppHydrator() {
  const hydrateAuth = useAuth((s) => s.hydrate);
  const hydrateCart = useCart((s) => s.hydrate);

  useEffect(() => {
    hydrateAuth();
    hydrateCart();
  }, [hydrateAuth, hydrateCart]);

  return null;
}
