"use client";

import { useRouter, usePathname } from "next/navigation";
import { ShoppingCart, Check } from "lucide-react";
import { useCart } from "@/hooks/useCart";
import { useAuth } from "@/hooks/useAuth";
import { InteractiveFormation } from "@/types";

export function AddFormationToCartButton({ formation }: { formation: InteractiveFormation }) {
  const { items, addFormation } = useCart();
  const { user, hydrated } = useAuth();
  const inCart = items.some((i) => i.type === "formation" && i.id === formation.id);
  const router = useRouter();
  const pathname = usePathname();

  function handleClick() {
    if (!hydrated) return;
    if (inCart) { router.push("/cart"); return; }
    if (!user) { router.push(`/login?next=${encodeURIComponent(pathname)}`); return; }
    addFormation(formation);
  }

  return (
    <button
      onClick={handleClick}
      className={inCart ? "btn-outline w-full !border-brand-600 !text-brand-700" : "btn-primary w-full"}
    >
      {inCart ? <Check size={18} /> : <ShoppingCart size={18} />}
      {inCart ? "Dans le panier · voir" : "S'inscrire à la formation"}
    </button>
  );
}
