"use client";

import { useRouter, usePathname } from "next/navigation";
import { ShoppingCart, Check, LogIn } from "lucide-react";
import { useCart } from "@/hooks/useCart";
import { useAuth } from "@/hooks/useAuth";
import { InteractiveFormation } from "@/types";

export function AddFormationToCartButton({ formation }: { formation: InteractiveFormation }) {
  const { items, addFormation } = useCart();
  const { user, hydrated } = useAuth();
  const inCart = items.some((i) => i.type === "formation" && i.id === formation.id);
  const router = useRouter();
  const pathname = usePathname();

  if (!user) {
    return (
      <button
        onClick={() => hydrated && router.push(`/login?next=${encodeURIComponent(pathname)}`)}
        className="btn-outline w-full"
      >
        <LogIn size={18} /> Se connecter pour s'inscrire
      </button>
    );
  }

  return (
    <button
      onClick={() => (inCart ? router.push("/cart") : addFormation(formation))}
      className={inCart ? "btn-outline w-full !border-brand-600 !text-brand-700" : "btn-primary w-full"}
    >
      {inCart ? <Check size={18} /> : <ShoppingCart size={18} />}
      {inCart ? "Dans le panier — voir" : "S'inscrire à la formation"}
    </button>
  );
}
