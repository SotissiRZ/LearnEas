"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useAuth } from "@/hooks/useAuth";

const COMMON_ROUTES = ["/courses", "/formations", "/mentorship", "/opportunities", "/pricing", "/about"];

function internalPathFromAnchor(anchor: HTMLAnchorElement): string | null {
  if (!anchor.href || anchor.target === "_blank" || anchor.hasAttribute("download")) return null;
  try {
    const url = new URL(anchor.href, window.location.href);
    if (url.origin !== window.location.origin) return null;
    if (url.pathname.startsWith("/api/") || url.pathname.startsWith("/admin/")) return null;
    return `${url.pathname}${url.search}${url.hash}`;
  } catch {
    return null;
  }
}

/**
 * Améliore la sensation de réactivité : précharge les routes au survol/idle et affiche
 * immédiatement une barre de progression quand une navigation interne démarre. En next dev,
 * une route lourde peut encore nécessiter une compilation à froid ; le clic reste néanmoins
 * visible et les navigations suivantes profitent du préchargement.
 */
export default function NavigationPerformance() {
  const router = useRouter();
  const pathname = usePathname();
  const user = useAuth((state) => state.user);
  const [navigating, setNavigating] = useState(false);
  const cleanupRef = useRef<(() => void) | null>(null);
  const prefetched = useRef(new Set<string>());

  useEffect(() => {
    setNavigating(false);
    cleanupRef.current?.();
    cleanupRef.current = null;
  }, [pathname]);

  useEffect(() => {
    const prefetch = (path: string) => {
      const key = path.split("#", 1)[0];
      if (!key || prefetched.current.has(key)) return;
      prefetched.current.add(key);
      router.prefetch(key);
    };

    const onPointerOver = (event: PointerEvent) => {
      const anchor = (event.target as Element | null)?.closest?.("a[href]") as HTMLAnchorElement | null;
      if (!anchor) return;
      const path = internalPathFromAnchor(anchor);
      if (path) prefetch(path);
    };
    const onFocusIn = (event: FocusEvent) => {
      const anchor = (event.target as Element | null)?.closest?.("a[href]") as HTMLAnchorElement | null;
      if (!anchor) return;
      const path = internalPathFromAnchor(anchor);
      if (path) prefetch(path);
    };
    const onClick = (event: MouseEvent) => {
      if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      const anchor = (event.target as Element | null)?.closest?.("a[href]") as HTMLAnchorElement | null;
      if (!anchor) return;
      const path = internalPathFromAnchor(anchor);
      if (!path) return;
      const target = new URL(anchor.href, window.location.href);
      if (`${target.pathname}${target.search}${target.hash}` === `${window.location.pathname}${window.location.search}${window.location.hash}`) return;

      setNavigating(true);
      const startHref = window.location.href;
      const interval = window.setInterval(() => {
        if (window.location.href !== startHref) {
          setNavigating(false);
          window.clearInterval(interval);
          window.clearTimeout(timeout);
        }
      }, 80);
      const timeout = window.setTimeout(() => {
        setNavigating(false);
        window.clearInterval(interval);
      }, 15000);
      cleanupRef.current?.();
      cleanupRef.current = () => {
        window.clearInterval(interval);
        window.clearTimeout(timeout);
      };
    };

    document.addEventListener("pointerover", onPointerOver, { passive: true });
    document.addEventListener("focusin", onFocusIn);
    document.addEventListener("click", onClick, true);

    let timeoutId: number | undefined;
    let idleId: number | undefined;
    const idleWindow = window as Window & {
      requestIdleCallback?: (cb: () => void, opts?: { timeout: number }) => number;
      cancelIdleCallback?: (id: number) => void;
    };
    const preloadCommon = () => {
      for (const path of COMMON_ROUTES) prefetch(path);
      if (user) {
        const dashboard = user.role === "admin" ? "/dashboard/admin" : user.role === "instructor" ? "/dashboard/instructor" : "/dashboard/student";
        prefetch(dashboard);
      }
    };
    if (typeof idleWindow.requestIdleCallback === "function") {
      idleId = idleWindow.requestIdleCallback(preloadCommon, { timeout: 2500 });
    } else {
      timeoutId = window.setTimeout(preloadCommon, 1200);
    }

    return () => {
      document.removeEventListener("pointerover", onPointerOver);
      document.removeEventListener("focusin", onFocusIn);
      document.removeEventListener("click", onClick, true);
      cleanupRef.current?.();
      if (timeoutId !== undefined) window.clearTimeout(timeoutId);
      if (idleId !== undefined && typeof idleWindow.cancelIdleCallback === "function") {
        idleWindow.cancelIdleCallback(idleId);
      }
    };
  }, [router, user]);

  if (!navigating) return null;
  return (
    <div className="pointer-events-none fixed inset-x-0 top-0 z-[200] h-1 overflow-hidden bg-brand-100" aria-hidden="true">
      <div className="h-full w-1/3 animate-[kalan-nav-progress_1s_ease-in-out_infinite] bg-brand-500" />
    </div>
  );
}
