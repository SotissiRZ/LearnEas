"use client";

import { create } from "zustand";
import { Course, PDFProduct, InteractiveFormation } from "@/types";

export interface CartItem {
  type: "course" | "pdf" | "formation";
  id: number;
  title: string;
  price: number;
  thumbnail: string | null;
  slug: string;
}

interface CartState {
  items: CartItem[];
  hydrated: boolean;
  hydrate: () => void;
  addCourse: (course: Course) => void;
  addPdf: (pdf: PDFProduct) => void;
  addFormation: (formation: InteractiveFormation) => void;
  remove: (type: "course" | "pdf" | "formation", id: number) => void;
  clear: () => void;
  total: () => number;
}

function persist(items: CartItem[]) {
  if (typeof window !== "undefined") {
    localStorage.setItem("learneas_cart", JSON.stringify(items));
  }
}

export const useCart = create<CartState>((set, get) => ({
  items: [],
  hydrated: false,

  hydrate: () => {
    if (typeof window === "undefined") return;
    const raw = localStorage.getItem("learneas_cart");
    set({ items: raw ? JSON.parse(raw) : [], hydrated: true });
  },

  addCourse: (course) => {
    if (get().items.some((i) => i.type === "course" && i.id === course.id)) return;
    const items = [
      ...get().items,
      {
        type: "course" as const,
        id: course.id,
        title: course.title,
        price: course.effective_price,
        thumbnail: course.thumbnail,
        slug: course.slug,
      },
    ];
    set({ items });
    persist(items);
  },

  addPdf: (pdf) => {
    if (get().items.some((i) => i.type === "pdf" && i.id === pdf.id)) return;
    const items = [
      ...get().items,
      {
        type: "pdf" as const,
        id: pdf.id,
        title: pdf.title,
        price: parseFloat(pdf.price),
        thumbnail: pdf.cover_image,
        slug: pdf.slug,
      },
    ];
    set({ items });
    persist(items);
  },

  addFormation: (formation) => {
    if (get().items.some((i) => i.type === "formation" && i.id === formation.id)) return;
    const items = [
      ...get().items,
      {
        type: "formation" as const,
        id: formation.id,
        title: formation.title,
        price: parseFloat(formation.price),
        thumbnail: formation.thumbnail,
        slug: formation.slug,
      },
    ];
    set({ items });
    persist(items);
  },

  remove: (type, id) => {
    const items = get().items.filter((i) => !(i.type === type && i.id === id));
    set({ items });
    persist(items);
  },

  clear: () => {
    set({ items: [] });
    persist([]);
  },

  total: () => get().items.reduce((sum, i) => sum + i.price, 0),
}));
