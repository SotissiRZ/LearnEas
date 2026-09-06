"use client";

import { useEffect, useRef } from "react";
import { usePathname } from "next/navigation";
import { trackProductEvent, type ProductEventName } from "@/lib/analytics";

function eventForPath(pathname: string): ProductEventName {
  if (/^\/courses\/[^/]+/.test(pathname)) return "course_viewed";
  if (/^\/formations\/[^/]+/.test(pathname)) return "formation_viewed";
  if (/^\/pdfs\/[^/]+/.test(pathname)) return "pdf_viewed";
  if (/^\/opportunities\/[^/]+/.test(pathname)) return "opportunity_viewed";
  return "page_view";
}

const PRIVATE_PREFIXES = ["/reset-password", "/verify-email", "/checkout/return", "/login", "/register"];

export default function ProductAnalytics() {
  const pathname = usePathname();
  const previous = useRef<string>("");

  useEffect(() => {
    if (!pathname || pathname === previous.current || PRIVATE_PREFIXES.some((prefix) => pathname.startsWith(prefix))) return;
    previous.current = pathname;
    // Ne jamais envoyer la query string : les recherches et paramètres privés restent locaux.
    trackProductEvent(eventForPath(pathname), { source: "navigation" }, pathname);
  }, [pathname]);

  return null;
}
