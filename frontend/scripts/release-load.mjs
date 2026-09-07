import process from "node:process";

const baseURL = (process.env.RELEASE_BASE_URL || "http://127.0.0.1:3000").replace(/\/+$/, "");
const parsedBase = new URL(baseURL);
const isLocalDev = ["127.0.0.1", "localhost", "0.0.0.0"].includes(parsedBase.hostname);
const total = Math.max(20, Math.min(5000, Number(process.env.RELEASE_LOAD_REQUESTS || (isLocalDev ? 60 : 180))));
const concurrency = Math.max(1, Math.min(100, Number(process.env.RELEASE_LOAD_CONCURRENCY || (isLocalDev ? 6 : 18))));
const timeoutMs = Math.max(250, Number(process.env.RELEASE_LOAD_TIMEOUT_MS || (isLocalDev ? 15000 : 5000)));
const maxP95 = Math.max(50, Number(process.env.RELEASE_LOAD_MAX_P95_MS || (isLocalDev ? 5000 : 1500)));
const maxErrorRate = Math.max(0, Math.min(1, Number(process.env.RELEASE_LOAD_MAX_ERROR_RATE || 0.01)));
const endpoints = ["/healthz", "/api/health/live", "/api/auth/platform-settings"];

const latencies = [];
let errors = 0;
let issued = 0;

async function timedFetch(endpoint, record = true) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const started = performance.now();
  try {
    const response = await fetch(`${baseURL}${endpoint}`, { signal: controller.signal, cache: "no-store", redirect: "manual" });
    await response.arrayBuffer();
    if (record) {
      if (!response.ok) errors += 1;
      latencies.push(performance.now() - started);
    }
    return response.ok;
  } catch {
    if (record) {
      errors += 1;
      latencies.push(performance.now() - started);
    }
    return false;
  } finally {
    clearTimeout(timer);
  }
}

if (isLocalDev) {
  for (const endpoint of endpoints) await timedFetch(endpoint, false);
}

async function one(index) {
  const endpoint = endpoints[index % endpoints.length];
  await timedFetch(endpoint, true);
}

async function worker() {
  while (true) {
    const index = issued++;
    if (index >= total) return;
    await one(index);
  }
}

const started = performance.now();
await Promise.all(Array.from({ length: concurrency }, () => worker()));
const elapsed = performance.now() - started;
latencies.sort((a, b) => a - b);
const pct = (p) => latencies[Math.min(latencies.length - 1, Math.max(0, Math.ceil(latencies.length * p) - 1))] || 0;
const p50 = pct(0.50);
const p95 = pct(0.95);
const p99 = pct(0.99);
const errorRate = errors / total;
const rps = total / (elapsed / 1000);

console.log(JSON.stringify({ mode: isLocalDev ? "local-dev" : "release", total, concurrency, timeout_ms: timeoutMs, max_p95_ms: maxP95, errors, error_rate: Number(errorRate.toFixed(4)), p50_ms: Math.round(p50), p95_ms: Math.round(p95), p99_ms: Math.round(p99), rps: Number(rps.toFixed(1)) }, null, 2));

if (p95 > maxP95) {
  console.error(`p95 ${Math.round(p95)}ms > threshold ${maxP95}ms`);
  process.exitCode = 1;
}
if (errorRate > maxErrorRate) {
  console.error(`error rate ${(errorRate * 100).toFixed(2)}% > threshold ${(maxErrorRate * 100).toFixed(2)}%`);
  process.exitCode = 1;
}
