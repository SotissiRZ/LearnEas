"use client";

import { useRouter } from "next/navigation";
import { ShoppingCart, Check } from "lucide-react";
import { useCart } from "@/hooks/useCart";
import { InteractiveFormation } from "@/types";

export function AddFormationToCartButton({ formation }: { formation: InteractiveFormation }) {
  const { items, addFormation } = useCart();
  const inCart = items.some((i) => i.type === "formation" && i.id === formation.id);
  const router = useRouter();

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
