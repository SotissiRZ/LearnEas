import { api } from "@/lib/api";

type AnalyticsValue = string | number | boolean | null | undefined;

export type ProductEventName =
  | "page_view"
  | "search_submitted"
  | "discovery_result_clicked"
  | "recommendation_clicked"
  | "course_viewed"
  | "formation_viewed"
  | "pdf_viewed"
  | "opportunity_viewed"
  | "video_started"
  | "video_completed";

const SESSION_KEY = "kalanpro_analytics_session_v1";

function sessionId(): string {
  if (typeof window === "undefined") return "";
  try {
    let value = sessionStorage.getItem(SESSION_KEY) || "";
    if (!value) {
      value = typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
      sessionStorage.setItem(SESSION_KEY, value);
    }
    return value;
  } catch {
    return "";
  }
}

export function trackProductEvent(
  eventName: ProductEventName,
  properties: Record<string, AnalyticsValue> = {},
  path?: string,
): void {
  if (typeof window === "undefined") return;
  const cleanProperties = Object.fromEntries(
    Object.entries(properties).filter(([, value]) => value !== undefined),
  );
  // Analytics ne doit jamais bloquer le parcours utilisateur. L'API serveur applique
  // ensuite une seconde whitelist et retire query strings / propriétés non autorisées.
  void api.post("/analytics/events/", {
    event_name: eventName,
    session_id: sessionId(),
    path: path || window.location.pathname,
    properties: cleanProperties,
  }).catch(() => undefined);
}
