/** @type {import('next').NextConfig} */
function externalOrigin(value) {
  if (!value || value.startsWith('/')) return '';
  try {
    const url = new URL(value);
    return ['http:', 'https:'].includes(url.protocol) ? url.origin : '';
  } catch {
    return '';
  }
}

const apiOrigin = externalOrigin(process.env.NEXT_PUBLIC_API_URL);
const connectSources = [
  "'self'",
  apiOrigin,
  'https://api.stripe.com',
  'https://www.youtube.com',
  'https://www.youtube-nocookie.com',
  'https://player.vimeo.com',
  'https://checkout.stripe.com',
  'https://youcanpay.com',
  'https://geniuspay.ci',
  'https://cdn.jsdelivr.net',
  'stun:', 'turn:', 'turns:', 'wss:', 'ws:',
].filter(Boolean).join(' ');

const frameSources = [
  "'self'",
  'blob:',
  apiOrigin,
  'https://www.youtube.com',
  'https://www.youtube-nocookie.com',
  'https://player.vimeo.com',
  'https://checkout.stripe.com',
  'https://youcanpay.com',
  'https://pay.genius.ci',
].filter(Boolean).join(' ');

const csp = [
  "default-src 'self'",
  "base-uri 'self'",
  "object-src 'none'",
  "frame-ancestors 'none'",
  "form-action 'self' https://checkout.stripe.com https://youcanpay.com https://pay.genius.ci",
  "img-src 'self' data: blob: https:",
  "media-src 'self' blob: https:",
  "font-src 'self' data:",
  "style-src 'self' 'unsafe-inline'",
  "script-src 'self' 'unsafe-inline' 'wasm-unsafe-eval' https://cdn.jsdelivr.net",
  "worker-src 'self' blob:",
  `connect-src ${connectSources}`,
  `frame-src ${frameSources}`,
].join('; ');

const nextConfig = {
  output: "standalone",
  images: { formats: ["image/avif", "image/webp"] },
  async headers() {
    return [{
      source: "/(.*)",
      headers: [
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        { key: "X-Frame-Options", value: "DENY" },
        { key: "Permissions-Policy", value: "camera=(self), microphone=(self), geolocation=(), payment=(self)" },
        { key: "Content-Security-Policy", value: csp },
      ],
    }];
  },
};
module.exports = nextConfig;
