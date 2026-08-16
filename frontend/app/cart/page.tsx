"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { Trash2, ShoppingBag, FileText, PlayCircle, Video, ArrowRight } from "lucide-react";
import { useCart } from "@/hooks/useCart";
import { useAuth } from "@/hooks/useAuth";
import { formatPrice } from "@/lib/api";

export default function CartPage() {
  const { items, remove, total } = useCart();
  const { user } = useAuth();
  const router = useRouter();

  function goToCheckout() {
    if (!user) {
      router.push("/login?next=/checkout");
      return;
    }
    router.push("/checkout");
  }

  if (items.length === 0) {
    return (
      <div className="container-app flex flex-col items-center gap-4 py-24 text-center">
        <ShoppingBag size={48} className="text-gray-300" />
        <h1 className="text-2xl font-bold">Votre panier est vide</h1>
        <p className="max-w-md text-gray-500">Parcourez notre catalogue de cours complets et de PDF pour commencer à apprendre.</p>
        <Link href="/courses" className="btn-primary">Explorer les cours</Link>
      </div>
    );
  }

  return (
    <div className="container-app grid grid-cols-1 gap-8 py-10 lg:grid-cols-[1fr_360px]">
      <div>
        <h1 className="mb-6 text-2xl font-extrabold">Panier ({items.length})</h1>
        <div className="flex flex-col gap-4">
          {items.map((item) => (
            <div key={`${item.type}-${item.id}`} className="card flex items-center gap-4 p-4">
              <div className="flex h-16 w-24 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-gray-100">
                {item.thumbnail ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={item.thumbnail} alt={item.title} className="h-full w-full object-cover" />
                ) : item.type === "course" ? (
                  <PlayCircle className="text-gray-300" />
                ) : item.type === "formation" ? (
                  <Video className="text-gray-300" />
                ) : (
                  <FileText className="text-gray-300" />
                )}
              </div>
              <div className="flex-1">
                <span className="badge mb-1 bg-gray-100 text-gray-600">
                  {item.type === "course" ? "Cours complet" : item.type === "formation" ? "Formation interactive" : "PDF"}
                </span>
                <p className="font-semibold">{item.title}</p>
              </div>
              <span className="font-bold">{formatPrice(item.price)}</span>
              <button onClick={() => remove(item.type, item.id)} className="rounded-lg p-2 text-gray-400 hover:bg-red-50 hover:text-red-600">
                <Trash2 size={18} />
              </button>
            </div>
          ))}
        </div>
      </div>

      <div>
        <div className="card sticky top-24 p-5">
          <h2 className="mb-4 text-lg font-bold">Résumé</h2>
          <div className="flex items-center justify-between border-t border-gray-100 pt-4 text-lg font-extrabold">
            <span>Total</span>
            <span>{formatPrice(total())}</span>
          </div>
          <button onClick={goToCheckout} className="btn-primary mt-5 w-full">
            Passer au paiement <ArrowRight size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
