import http from "node:http";
import process from "node:process";

const target = new URL((process.env.RELEASE_BASE_URL || "http://127.0.0.1:3000").replace(/\/+$/, ""));
const attempts = Math.max(12, Math.min(200, Number(process.env.RELEASE_CHAOS_REQUESTS || 36)));
const clientTimeoutMs = Math.max(200, Number(process.env.RELEASE_CHAOS_CLIENT_TIMEOUT_MS || 900));
const maxRetries = 2;
let sequence = 0;

const proxy = http.createServer((req, res) => {
  sequence += 1;
  const current = sequence;
  // Deterministic fault pattern: synthetic 503 and delayed connections.
  if (current % 7 === 0) {
    res.writeHead(503, { "content-type": "application/json" });
    res.end('{"detail":"synthetic network fault"}');
    return;
  }

  const forward = () => {
    const upstream = http.request({
      hostname: target.hostname,
      port: target.port || 80,
      method: req.method,
      path: req.url,
      headers: { ...req.headers, host: target.host },
    }, (upstreamRes) => {
      res.writeHead(upstreamRes.statusCode || 502, upstreamRes.headers);
      upstreamRes.pipe(res);
    });
    upstream.on("error", () => {
      if (!res.headersSent) res.writeHead(502);
      res.end();
    });
    req.pipe(upstream);
  };

  if (current % 5 === 0) setTimeout(forward, clientTimeoutMs + 250);
  else forward();
});

await new Promise((resolve) => proxy.listen(0, "127.0.0.1", resolve));
const port = proxy.address().port;

async function resilientGet(path) {
  for (let attempt = 0; attempt <= maxRetries; attempt += 1) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), clientTimeoutMs);
    try {
      const response = await fetch(`http://127.0.0.1:${port}${path}`, { signal: controller.signal, cache: "no-store" });
      if (response.ok) {
        await response.arrayBuffer();
        clearTimeout(timer);
        return true;
      }
    } catch {
      // A timeout/drop is an expected injected fault. Retry idempotent GETs only.
    } finally {
      clearTimeout(timer);
    }
  }
  return false;
}

let succeeded = 0;
try {
  for (let i = 0; i < attempts; i += 1) {
    const path = i % 2 === 0 ? "/api/health/live/" : "/api/auth/platform-settings/";
    if (await resilientGet(path)) succeeded += 1;
  }
} finally {
  await new Promise((resolve) => proxy.close(resolve));
}

const successRate = succeeded / attempts;
console.log(JSON.stringify({ attempts, succeeded, success_rate: Number(successRate.toFixed(4)), injected_fault_pattern: "503-every-7th, delay-every-5th", retries: maxRetries }, null, 2));
if (successRate < 0.9) {
  console.error(`resilience success rate ${(successRate * 100).toFixed(1)}% < 90%`);
  process.exit(1);
}
