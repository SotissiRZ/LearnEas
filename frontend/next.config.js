/** @type {import('next').NextConfig} */
function proxyTarget(value) {
  if (!value) return '';
  try {
    const url = new URL(value);
    if (!['http:', 'https:'].includes(url.protocol)) return '';
    return `${url.origin}${url.pathname.replace(/\/+$/, '')}`;
  } catch {
    return '';
  }
}

const apiProxyTarget = proxyTarget(process.env.API_PROXY_TARGET);
const distDir = process.env.NEXT_DIST_DIR || ".next";

const nextConfig = {
  distDir,
  poweredByHeader: false,
  output: "standalone",
  images: { formats: ["image/avif", "image/webp"] },
  async rewrites() {
    if (!apiProxyTarget) return [];
    return [
      // Django/DRF routes use trailing slashes. Next normalises the incoming pathname before an
      // external rewrite, so explicitly restore the slash on the upstream destination; otherwise
      // POST endpoints such as /auth/login/ arrive as /auth/login and APPEND_SLASH cannot safely
      // redirect a POST body (500).
      { source: "/api/:path*", destination: `${apiProxyTarget}/api/:path*/` },
      { source: "/admin/:path*", destination: `${apiProxyTarget}/admin/:path*` },
      { source: "/static/:path*", destination: `${apiProxyTarget}/static/:path*` },
      { source: "/media/:path*", destination: `${apiProxyTarget}/media/:path*` },
    ];
  },
  async headers() {
    return [{
      source: "/(.*)",
      headers: [
        { key: "X-Content-Type-Options", value: "nosniff" },
        { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        { key: "Permissions-Policy", value: "camera=(self), microphone=(self), geolocation=(), payment=(self)" },
      ],
    }];
  },
};
module.exports = nextConfig;
