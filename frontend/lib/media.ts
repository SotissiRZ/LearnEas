/**
 * Résout les URLs médias renvoyées par l'API.
 *
 * En local Docker, NEXT_PUBLIC_API_URL vaut généralement "/api" et une URL
 * protégée `/api/media/private/?token=...` doit rester same-origin pour passer
 * par Nginx. En production Vercel + Railway, NEXT_PUBLIC_API_URL peut être
 * absolue ; on rattache alors les URLs `/api/...` à l'origine du backend.
 */
export function resolveMediaUrl(value: string): string {
  const raw = (value || "").trim();
  if (!raw) return raw;
  if (/^(https?:|blob:|data:)/i.test(raw)) return raw;

  const publicApi = process.env.NEXT_PUBLIC_API_URL || "/api";
  if (raw.startsWith("/api/") && /^https?:\/\//i.test(publicApi)) {
    try {
      return `${new URL(publicApi).origin}${raw}`;
    } catch {
      return raw;
    }
  }
  return raw;
}
