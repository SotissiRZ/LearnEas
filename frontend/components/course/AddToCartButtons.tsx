"use client";

import { useRouter, usePathname } from "next/navigation";
import { ShoppingCart, Check, LogIn } from "lucide-react";
import { useCart } from "@/hooks/useCart";
import { useAuth } from "@/hooks/useAuth";
import { Course, PDFProduct } from "@/types";

/**
 * Un achat doit toujours être rattaché à un compte (c'est ce compte qui recevra l'accès
 * après paiement). On exige donc la connexion AVANT d'ajouter quoi que ce soit au panier,
 * plutôt que de laisser un panier "anonyme" dont on ne saurait pas à qui l'attribuer.
 */
function useRequireAuthForCart() {
  const { user, hydrated } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  function requireAuth(action: () => void) {
    if (!hydrated) return;
    if (!user) {
      router.push(`/login?next=${encodeURIComponent(pathname)}`);
      return;
    }
    action();
  }

  return requireAuth;
}

export function AddCourseToCartButton({ course }: { course: Course }) {
  const { items, addCourse } = useCart();
  const { user } = useAuth();
  const requireAuth = useRequireAuthForCart();
  const inCart = items.some((i) => i.type === "course" && i.id === course.id);
  const router = useRouter();

  if (!user) {
    return (
      <button onClick={() => requireAuth(() => {})} className="btn-outline w-full">
        <LogIn size={18} /> Se connecter pour acheter
      </button>
    );
  }

  return (
    <button
      onClick={() => (inCart ? router.push("/cart") : requireAuth(() => addCourse(course)))}
      className={inCart ? "btn-outline w-full !border-brand-600 !text-brand-700" : "btn-primary w-full"}
    >
      {inCart ? <Check size={18} /> : <ShoppingCart size={18} />}
      {inCart ? "Dans le panier — voir" : "Ajouter au panier"}
    </button>
  );
}

export function AddPdfToCartButton({ pdf }: { pdf: PDFProduct }) {
  const { items, addPdf } = useCart();
  const { user } = useAuth();
  const requireAuth = useRequireAuthForCart();
  const inCart = items.some((i) => i.type === "pdf" && i.id === pdf.id);
  const router = useRouter();

  if (!user) {
    return (
      <button onClick={() => requireAuth(() => {})} className="btn-outline w-full">
        <LogIn size={18} /> Se connecter pour acheter
      </button>
    );
  }

  return (
    <button
      onClick={() => (inCart ? router.push("/cart") : requireAuth(() => addPdf(pdf)))}
      className={inCart ? "btn-outline w-full !border-brand-600 !text-brand-700" : "btn-primary w-full"}
    >
      {inCart ? <Check size={18} /> : <ShoppingCart size={18} />}
      {inCart ? "Dans le panier — voir" : "Ajouter au panier"}
    </button>
  );
}
