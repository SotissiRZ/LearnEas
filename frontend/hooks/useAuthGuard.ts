"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import type { AuthUser } from "@/types";

interface Options {
  /** Si fourni, seuls ces rôles peuvent accéder à la page. */
  roles?: Array<AuthUser["role"]>;
  /** Où rediriger si le rôle ne correspond pas (défaut: page d'accueil). */
  redirectTo?: string;
}

/**
 * Protège une page cliente : redirige vers /login si l'utilisateur n'est pas connecté,
 * ou vers `redirectTo` si son rôle ne correspond pas à `roles`.
 *
 * `ready` ne devient `true` que lorsque l'utilisateur est confirmé authentifié
 * (et autorisé) · tant que ce n'est pas le cas, la page ne doit RIEN afficher
 * de sensible (c'est ce qui causait l'accès au dashboard sans connexion).
 */
export function useAuthGuard(options: Options = {}) {
  const { user, hydrated } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const authorized = !!user && (!options.roles || options.roles.includes(user.role));

  useEffect(() => {
    if (!hydrated) return; // on attend la restauration sécurisée via le cookie HttpOnly

    if (!user) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
      return;
    }
    if (options.roles && !options.roles.includes(user.role)) {
      router.replace(options.redirectTo || "/");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hydrated, user, pathname]);

  return {
    user,
    /** true seulement quand on peut afficher le contenu protégé en toute sécurité */
    ready: hydrated && authorized,
    /** true tant que la session HttpOnly n'a pas encore été restaurée ou rejetée */
    checking: !hydrated,
  };
}
