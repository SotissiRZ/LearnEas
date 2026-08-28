"use client";

import { useRouter, usePathname } from "next/navigation";
import { ShoppingCart, Check } from "lucide-react";
import { useCart } from "@/hooks/useCart";
import { useAuth } from "@/hooks/useAuth";
import { Course, PDFProduct } from "@/types";

/**
 * Un achat doit toujours être rattaché à un compte (c'est ce compte qui recevra l'accès
 * après paiement). Le bouton reste TOUJOURS le même (achat), qu'on soit connecté ou non :
 * si l'utilisateur n'est pas connecté, le clic redirige vers /login puis revient ici,
 * plutôt que de changer l'apparence/le texte du bouton selon l'état de connexion.
 */
export function AddCourseToCartButton({ course }: { course: Course }) {
  const { items, addCourse } = useCart();
  const { user, hydrated } = useAuth();
  const inCart = items.some((i) => i.type === "course" && i.id === course.id);
  const router = useRouter();
  const pathname = usePathname();

  function handleClick() {
    if (!hydrated) return;
    if (inCart) { router.push("/cart"); return; }
    if (!user) { router.push(`/login?next=${encodeURIComponent(pathname)}`); return; }
    addCourse(course);
  }

  return (
    <button
      onClick={handleClick}
      className={inCart ? "btn-outline w-full !border-brand-600 !text-brand-700" : "btn-primary w-full"}
    >
      {inCart ? <Check size={18} /> : <ShoppingCart size={18} />}
      {inCart ? "Dans le panier — voir" : "Ajouter au panier"}
    </button>
  );
}

export function AddPdfToCartButton({ pdf }: { pdf: PDFProduct }) {
  const { items, addPdf } = useCart();
  const { user, hydrated } = useAuth();
  const inCart = items.some((i) => i.type === "pdf" && i.id === pdf.id);
  const router = useRouter();
  const pathname = usePathname();

  function handleClick() {
    if (!hydrated) return;
    if (inCart) { router.push("/cart"); return; }
    if (!user) { router.push(`/login?next=${encodeURIComponent(pathname)}`); return; }
    addPdf(pdf);
  }

  return (
    <button
      onClick={handleClick}
      className={inCart ? "btn-outline w-full !border-brand-600 !text-brand-700" : "btn-primary w-full"}
    >
      {inCart ? <Check size={18} /> : <ShoppingCart size={18} />}
      {inCart ? "Dans le panier — voir" : "Ajouter au panier"}
    </button>
  );
}
