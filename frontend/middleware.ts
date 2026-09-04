import { NextRequest, NextResponse } from "next/server";

function externalOrigin(value?: string): string {
  if (!value || value.startsWith("/")) return "";
  try {
    const url = new URL(value);
    return ["http:", "https:", "ws:", "wss:"].includes(url.protocol) ? url.origin : "";
  } catch {
    return "";
  }
}

function mainCsp(nonce: string): string {
  const devEval = process.env.NODE_ENV === "development" ? " 'unsafe-eval'" : "";
  const apiOrigin = externalOrigin(process.env.NEXT_PUBLIC_API_URL);
  const mediaOrigin = externalOrigin(process.env.NEXT_PUBLIC_MEDIA_ORIGIN);
  const wsOrigin = externalOrigin(process.env.NEXT_PUBLIC_WS_URL);
  const connectSources = [
    "'self'",
    apiOrigin,
    mediaOrigin,
    wsOrigin,
    "https://api.stripe.com",
    "https://www.youtube.com",
    "https://www.youtube-nocookie.com",
    "https://player.vimeo.com",
    "https://checkout.stripe.com",
    "https://youcanpay.com",
    "https://geniuspay.ci",
  ].filter(Boolean).join(" ");

  const frameSources = [
    "'self'",
    apiOrigin,
    "https://www.youtube.com",
    "https://www.youtube-nocookie.com",
    "https://player.vimeo.com",
    "https://checkout.stripe.com",
    "https://youcanpay.com",
    "https://pay.genius.ci",
  ].filter(Boolean).join(" ");

  return [
    "default-src 'self'",
    "base-uri 'self'",
    "object-src 'none'",
    "frame-ancestors 'none'",
    "form-action 'self' https://checkout.stripe.com https://youcanpay.com https://pay.genius.ci",
    "img-src 'self' data: blob: https:",
    "media-src 'self' blob: https:",
    "font-src 'self' data:",
    // Next/Tailwind et plusieurs composants utilisent encore des attributs style calculés.
    // Le risque script est traité séparément : aucun `unsafe-inline` n'est autorisé pour JS.
    "style-src 'self' 'unsafe-inline'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${devEval}`,
    "worker-src 'self' blob:",
    "manifest-src 'self'",
    `connect-src ${connectSources}`,
    `frame-src ${frameSources}`,
  ].join("; ");
}

const runnerCsp = [
  "default-src 'none'",
  "base-uri 'none'",
  "object-src 'none'",
  "frame-ancestors 'self'",
  "script-src 'self' https://cdn.jsdelivr.net 'wasm-unsafe-eval'",
  "worker-src blob:",
  "connect-src https://cdn.jsdelivr.net",
  "img-src data: blob:",
  "style-src 'none'",
].join("; ");

export function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  const isRunner = pathname.startsWith("/code-runner/");
  if (isRunner) {
    const response = NextResponse.next();
    response.headers.set("Content-Security-Policy", runnerCsp);
    response.headers.set("Cross-Origin-Resource-Policy", "same-origin");
    response.headers.set("X-Frame-Options", "SAMEORIGIN");
    response.headers.set("Cache-Control", "public, max-age=3600");
    return response;
  }

  const nonce = btoa(crypto.randomUUID());
  const csp = mainCsp(nonce);
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set("x-nonce", nonce);
  requestHeaders.set("Content-Security-Policy", csp);

  const response = NextResponse.next({ request: { headers: requestHeaders } });
  response.headers.set("Content-Security-Policy", csp);
  response.headers.set("X-Frame-Options", "DENY");
  return response;
}

export const config = {
  matcher: [
    "/((?!api|_next/static|_next/image|favicon.ico|robots.txt|sitemap.xml).*)",
  ],
};
