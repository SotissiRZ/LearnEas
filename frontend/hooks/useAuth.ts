"use client";

import { create } from "zustand";
import { api } from "@/lib/api";
import { AuthUser } from "@/types";

interface AuthState {
  user: AuthUser | null;
  hydrated: boolean;
  hydrate: () => void;
  login: (email: string, password: string) => Promise<AuthUser>;
  register: (payload: Record<string, string>) => Promise<AuthUser>;
  logout: () => Promise<void>;
  refreshMe: () => Promise<void>;
}

export const useAuth = create<AuthState>((set, get) => ({
  user: null,
  hydrated: false,

  hydrate: () => {
    if (typeof window === "undefined") return;
    const raw = localStorage.getItem("learneas_user");
    set({ user: raw ? JSON.parse(raw) : null, hydrated: true });
  },

  login: async (email, password) => {
    const data = await api.post<{ access: string; refresh: string; user: AuthUser }>(
      "/auth/login/",
      { email, password }
    );
    localStorage.setItem("learneas_access", data.access);
    localStorage.setItem("learneas_refresh", data.refresh);
    localStorage.setItem("learneas_user", JSON.stringify(data.user));
    set({ user: data.user });
    return data.user;
  },

  register: async (payload) => {
    const data = await api.post<{ access: string; refresh: string; user: AuthUser }>(
      "/auth/register/",
      payload
    );
    localStorage.setItem("learneas_access", data.access);
    localStorage.setItem("learneas_refresh", data.refresh);
    localStorage.setItem("learneas_user", JSON.stringify(data.user));
    set({ user: data.user });
    return data.user;
  },

  logout: async () => {
    const refresh = typeof window !== "undefined" ? localStorage.getItem("learneas_refresh") : null;
    try {
      if (refresh) await api.post("/auth/logout/", { refresh });
    } catch {
      // La déconnexion locale doit toujours fonctionner, même si le réseau est indisponible.
    } finally {
      localStorage.removeItem("learneas_access");
      localStorage.removeItem("learneas_refresh");
      localStorage.removeItem("learneas_user");
      set({ user: null });
    }
  },

  refreshMe: async () => {
    if (!get().user) return;
    const me = await api.get<AuthUser>("/auth/me/");
    localStorage.setItem("learneas_user", JSON.stringify(me));
    set({ user: me });
  },
}));
