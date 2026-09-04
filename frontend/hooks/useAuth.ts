"use client";

import { create } from "zustand";
import { api, clearClientSession, restoreAccessToken, setAccessToken } from "@/lib/api";
import { AuthUser } from "@/types";
import { useCart } from "@/hooks/useCart";

interface AuthState {
  user: AuthUser | null;
  hydrated: boolean;
  hydrate: () => Promise<void>;
  login: (email: string, password: string) => Promise<AuthUser>;
  register: (payload: Record<string, string>) => Promise<AuthUser>;
  logout: () => Promise<void>;
  refreshMe: () => Promise<void>;
}

function persistPublicUser(user: AuthUser | null) {
  if (typeof window === "undefined") return;
  if (user) localStorage.setItem("learneas_user", JSON.stringify(user));
  else localStorage.removeItem("learneas_user");
}

export const useAuth = create<AuthState>((set, get) => ({
  user: null,
  hydrated: false,

  hydrate: async () => {
    if (typeof window === "undefined") return;
    // Ne jamais considérer le profil localStorage comme une preuve d'authentification. La session
    // n'est déclarée prête qu'après rotation du cookie HttpOnly puis lecture de /auth/me/.
    set({ hydrated: false });
    try {
      const restored = await restoreAccessToken();
      if (!restored) {
        persistPublicUser(null);
        set({ user: null, hydrated: true });
        return;
      }
      const me = await api.get<AuthUser>("/auth/me/");
      persistPublicUser(me);
      set({ user: me, hydrated: true });
    } catch {
      clearClientSession();
      set({ user: null, hydrated: true });
    }
  },

  login: async (email, password) => {
    const data = await api.post<{ access: string; user: AuthUser }>(
      "/auth/login/",
      { email, password }
    );
    setAccessToken(data.access);
    persistPublicUser(data.user);
    set({ user: data.user, hydrated: true });
    return data.user;
  },

  register: async (payload) => {
    const data = await api.post<{ access: string; user: AuthUser }>(
      "/auth/register/",
      payload
    );
    setAccessToken(data.access);
    persistPublicUser(data.user);
    set({ user: data.user, hydrated: true });
    return data.user;
  },

  logout: async () => {
    useCart.getState().clear();
    try {
      await api.post("/auth/logout/");
    } catch {
      // La déconnexion locale doit toujours fonctionner, même si le réseau est indisponible.
    } finally {
      clearClientSession();
      persistPublicUser(null);
      set({ user: null, hydrated: true });
    }
  },

  refreshMe: async () => {
    if (!get().user) return;
    const me = await api.get<AuthUser>("/auth/me/");
    persistPublicUser(me);
    set({ user: me });
  },
}));
