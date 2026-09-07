import process from "node:process";

const args = new Set(process.argv.slice(2));
const baseURL = (process.env.RELEASE_BASE_URL || "http://127.0.0.1:3000").replace(/\/+$/, "");
const apiBase = (process.env.RELEASE_API_BASE_URL || `${baseURL}/api`).replace(/\/+$/, "");
const timeoutMs = Number(process.env.RELEASE_SMOKE_TIMEOUT_MS || 8000);
const useDemoAuth = args.has("--demo-auth");

const failures = [];
const timings = [];

async function request(url, init = {}, expected = [200]) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const started = performance.now();
  try {
    const response = await fetch(url, { redirect: "manual", ...init, signal: controller.signal });
    timings.push({ url, ms: Math.round(performance.now() - started), status: response.status });
    if (!expected.includes(response.status)) {
      const body = await response.text().catch(() => "");
      throw new Error(`HTTP ${response.status} ${body.slice(0, 180)}`);
    }
    return response;
  } finally {
    clearTimeout(timer);
  }
}

async function check(name, fn) {
  try {
    await fn();
    console.log(`✔ ${name}`);
  } catch (error) {
    failures.push(`${name}: ${error instanceof Error ? error.message : String(error)}`);
    console.error(`✖ ${name}`);
  }
}

await check("frontend liveness /healthz", async () => {
  const response = await request(`${baseURL}/healthz`);
  const text = await response.text();
  if (text.trim() !== "ok") throw new Error(`unexpected body: ${text.slice(0, 80)}`);
});

await check("backend liveness through same-origin proxy", async () => {
  const response = await request(`${apiBase}/health/live/`);
  const payload = await response.json();
  if (payload.status !== "ok") throw new Error("backend liveness is not ok");
  if (!response.headers.get("x-request-id")) throw new Error("missing X-Request-ID");
});

await check("backend readiness", async () => {
  const response = await request(`${apiBase}/health/ready/`);
  const payload = await response.json();
  if (payload.status !== "ok" || payload.checks?.database !== "ok" || payload.checks?.cache !== "ok") {
    throw new Error(`readiness=${JSON.stringify(payload)}`);
  }
});

const publicApis = [
  ["platform settings", "/auth/platform-settings/"],
  ["course catalogue", "/catalog/courses/?page_size=1"],
  ["PDF catalogue", "/catalog/pdfs/?page_size=1"],
  ["opportunities catalogue", "/opportunities/listings/?page_size=1"],
];
for (const [label, path] of publicApis) {
  await check(`public API · ${label}`, async () => {
    const response = await request(`${apiBase}${path}`);
    const type = response.headers.get("content-type") || "";
    if (!type.includes("application/json")) throw new Error(`unexpected content-type ${type}`);
    await response.json();
  });
}

const publicPages = ["/", "/courses", "/pdfs", "/opportunities", "/pricing", "/contact", "/support", "/login", "/register"];
for (const path of publicPages) {
  await check(`public page · ${path}`, async () => {
    const response = await request(`${baseURL}${path}`);
    const type = response.headers.get("content-type") || "";
    if (!type.includes("text/html")) throw new Error(`unexpected content-type ${type}`);
    if ((response.headers.get("x-content-type-options") || "").toLowerCase() !== "nosniff") {
      throw new Error("missing X-Content-Type-Options=nosniff");
    }
    if (!response.headers.get("content-security-policy")) throw new Error("missing Content-Security-Policy");
  });
}

if (useDemoAuth) {
  const email = process.env.RELEASE_SMOKE_EMAIL || "admin@kalanpro.com";
  const password = process.env.RELEASE_SMOKE_PASSWORD || "admin1234";
  let access = "";

  await check("demo admin login", async () => {
    const response = await request(`${apiBase}/auth/login/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const payload = await response.json();
    access = String(payload.access || "");
    if (!access) throw new Error("login returned no access token");
    if (payload.user?.role !== "admin") throw new Error(`unexpected role ${payload.user?.role}`);
  });

  await check("authenticated /auth/me", async () => {
    const response = await request(`${apiBase}/auth/me/`, { headers: { Authorization: `Bearer ${access}` } });
    const payload = await response.json();
    if (payload.role !== "admin") throw new Error(`unexpected role ${payload.role}`);
  });

  await check("admin operations health", async () => {
    const response = await request(`${apiBase}/ops/health/`, { headers: { Authorization: `Bearer ${access}` } });
    const payload = await response.json();
    if (!payload.services?.database || !payload.metrics) throw new Error("operations snapshot incomplete");
  });
}

const slowest = [...timings].sort((a, b) => b.ms - a.ms).slice(0, 5);
console.log(`\nSmoke timings (${timings.length} requests) · slowest: ${slowest.map((x) => `${x.status} ${x.ms}ms ${x.url}`).join(" | ")}`);

if (failures.length) {
  console.error("\nRelease smoke failed:");
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}
console.log("\nRelease smoke: OK");
