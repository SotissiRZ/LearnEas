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

const nextConfig = {
  output: "standalone",
  images: { formats: ["image/avif", "image/webp"] },
  async rewrites() {
    if (!apiProxyTarget) return [];
    return [{
      source: "/api/:path*",
      destination: `${apiProxyTarget}/api/:path*`,
    }];
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
