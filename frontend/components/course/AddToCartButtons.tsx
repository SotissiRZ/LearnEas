"use client";

import { useRouter } from "next/navigation";
import { ShoppingCart, Check } from "lucide-react";
import { useCart } from "@/hooks/useCart";
import { Course, PDFProduct } from "@/types";

export function AddCourseToCartButton({ course }: { course: Course }) {
  const { items, addCourse } = useCart();
  const inCart = items.some((i) => i.type === "course" && i.id === course.id);
  const router = useRouter();

  return (
    <button
      onClick={() => (inCart ? router.push("/cart") : addCourse(course))}
      className={inCart ? "btn-outline w-full !border-brand-600 !text-brand-700" : "btn-primary w-full"}
    >
      {inCart ? <Check size={18} /> : <ShoppingCart size={18} />}
      {inCart ? "Dans le panier — voir" : "Ajouter au panier"}
    </button>
  );
}

export function AddPdfToCartButton({ pdf }: { pdf: PDFProduct }) {
  const { items, addPdf } = useCart();
  const inCart = items.some((i) => i.type === "pdf" && i.id === pdf.id);
  const router = useRouter();

  return (
    <button
      onClick={() => (inCart ? router.push("/cart") : addPdf(pdf))}
      className={inCart ? "btn-outline w-full !border-brand-600 !text-brand-700" : "btn-primary w-full"}
    >
      {inCart ? <Check size={18} /> : <ShoppingCart size={18} />}
      {inCart ? "Dans le panier — voir" : "Ajouter au panier"}
    </button>
  );
}
