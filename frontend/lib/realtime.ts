export interface RealtimeUrlOptions {
  sessionId: number;
  ticket: string;
  explicitBase?: string;
  pageProtocol?: string;
  pageHost?: string;
}

function normalizeWsBase(value: string): string {
  const raw = value.trim().replace(/\/+$/, "");
  if (!raw) return "";
  try {
    const url = new URL(raw);
    if (!['ws:', 'wss:'].includes(url.protocol)) return "";
    return `${url.origin}${url.pathname.replace(/\/+$/, "")}`;
  } catch {
    return "";
  }
}

export function buildRealtimeWebSocketUrl(options: RealtimeUrlOptions): string {
  const explicit = normalizeWsBase(options.explicitBase || "");
  let base = explicit;
  if (!base) {
    const scheme = options.pageProtocol === "https:" ? "wss:" : "ws:";
    const host = String(options.pageHost || "").trim();
    if (!host) throw new Error("Hôte WebSocket indisponible.");
    base = `${scheme}//${host}/ws`;
  }
  return `${base}/sessions/${encodeURIComponent(String(options.sessionId))}/?ticket=${encodeURIComponent(options.ticket)}`;
}
