"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

/**
 * Hydrates a public SSR resource again in the browser so localStorage JWT
 * entitlements (purchase/enrollment/owner access) are reflected without
 * sacrificing the server-rendered public page.
 */
export function useAuthenticatedResource<T>(endpoint: string, initial: T): T {
  const [resource, setResource] = useState<T>(initial);

  useEffect(() => {
    let active = true;
    api.get<T>(endpoint)
      .then((value) => { if (active) setResource(value); })
      .catch(() => { /* Keep the public SSR snapshot when refresh fails. */ });
    return () => { active = false; };
  }, [endpoint]);

  return resource;
}
