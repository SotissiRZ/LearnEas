"use client";

import { useRouter, usePathname } from "next/navigation";
import { ShoppingCart, Check } from "lucide-react";
import { useCart } from "@/hooks/useCart";
import { useAuth } from "@/hooks/useAuth";
import { Course, PDFProduct, InteractiveFormation } from "@/types";

type Item =
  | { kind: "course"; data: Course }
  | { kind: "pdf"; data: PDFProduct }
  | { kind: "formation"; data: InteractiveFormation };

/**
 * Bouton d'achat rapide affiché directement sur une carte (catalogue), sans devoir ouvrir
 * la fiche détail. Empêche la navigation du <Link> parent qui enveloppe la carte.
 */
export default function QuickAddButton({ item }: { item: Item }) {
  const { items, addCourse, addPdf, addFormation } = useCart();
  const { user, hydrated } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const inCart = items.some((i) => i.type === item.kind && i.id === item.data.id);
  const isFull = item.kind === "formation" && (item.data as InteractiveFormation).is_full;

  function handleClick(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();

    if (!hydrated) return;

    if (inCart) {
      router.push("/cart");
      return;
    }
    if (!user) {
      router.push(`/login?next=${encodeURIComponent(pathname)}`);
      return;
    }
    if (item.kind === "course") addCourse(item.data as Course);
    else if (item.kind === "pdf") addPdf(item.data as PDFProduct);
    else addFormation(item.data as InteractiveFormation);
  }

  if (isFull) {
    return (
      <button disabled className="btn-outline !py-1.5 !text-xs cursor-not-allowed opacity-50">
        Complet
      </button>
    );
  }

  return (
    <button
      onClick={handleClick}
      className={
        inCart
          ? "btn-outline !py-1.5 !text-xs !border-brand-600 !text-brand-700"
          : "btn-primary !py-1.5 !text-xs"
      }
    >
      {inCart ? <Check size={14} /> : <ShoppingCart size={14} />}
      {inCart ? "Au panier" : "Ajouter"}
    </button>
  );
}
