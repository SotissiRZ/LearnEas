const baseURL = String(process.env.RELEASE_BASE_URL || "").replace(/\/+$/, "");
const backendURL = String(process.env.RELEASE_BACKEND_URL || "").replace(/\/+$/, "");
const timeoutMs = Number(process.env.RELEASE_SMOKE_TIMEOUT_MS || 10000);

if (!baseURL) {
  console.error("RELEASE_BASE_URL est requis (URL HTTPS Vercel). ");
  process.exit(1);
}

function ensureHttps(name, value) {
  let parsed;
  try { parsed = new URL(value); } catch { throw new Error(`${name} URL invalide`); }
  if (parsed.protocol !== "https:") throw new Error(`${name} doit utiliser https://`);
  if (["localhost", "127.0.0.1", "0.0.0.0"].includes(parsed.hostname)) throw new Error(`${name} ne peut pas pointer vers localhost`);
  return parsed;
}

const frontend = ensureHttps("RELEASE_BASE_URL", baseURL);
if (backendURL) ensureHttps("RELEASE_BACKEND_URL", backendURL);

const failures = [];
const timings = [];

async function request(url, init = {}, expected = [200]) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  const started = performance.now();
  try {
    const response = await fetch(url, { redirect: "manual", ...init, signal: controller.signal });
    timings.push({ url, status: response.status, ms: Math.round(performance.now() - started) });
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
    const message = error instanceof Error ? error.message : String(error);
    failures.push(`${name}: ${message}`);
    console.error(`✖ ${name}: ${message}`);
  }
}

await check("frontend HTTPS liveness", async () => {
  const response = await request(`${baseURL}/healthz`);
  if ((await response.text()).trim() !== "ok") throw new Error("body != ok");
});

await check("same-origin API liveness", async () => {
  const response = await request(`${baseURL}/api/health/live`);
  const payload = await response.json();
  if (payload.status !== "ok") throw new Error("backend status != ok");
  if (!response.headers.get("x-request-id")) throw new Error("X-Request-ID absent");
});

await check("same-origin API readiness", async () => {
  const response = await request(`${baseURL}/api/health/ready`);
  const payload = await response.json();
  if (payload.status !== "ok" || payload.checks?.database !== "ok" || payload.checks?.cache !== "ok") {
    throw new Error(JSON.stringify(payload));
  }
});

if (backendURL) {
  await check("backend Railway direct liveness", async () => {
    const response = await request(`${backendURL}/api/health/live/`, {
      headers: { Origin: frontend.origin },
    });
    const allowOrigin = response.headers.get("access-control-allow-origin") || "";
    if (allowOrigin !== frontend.origin) throw new Error(`CORS=${allowOrigin || "absent"}`);
    if (allowOrigin === "*") throw new Error("CORS wildcard interdit");
  });
}

for (const path of ["/", "/courses", "/pdfs", "/opportunities", "/pricing", "/support", "/login"]) {
  await check(`page ${path}`, async () => {
    const response = await request(`${baseURL}${path}`);
    const type = response.headers.get("content-type") || "";
    if (!type.includes("text/html")) throw new Error(`content-type=${type}`);
    if ((response.headers.get("x-content-type-options") || "").toLowerCase() !== "nosniff") {
      throw new Error("X-Content-Type-Options manquant");
    }
    if (!response.headers.get("content-security-policy")) throw new Error("CSP absente");
  });
}

for (const path of [
  "/api/auth/platform-settings",
  "/api/catalog/courses?page_size=1",
  "/api/catalog/pdfs?page_size=1",
  "/api/opportunities/listings?page_size=1",
]) {
  await check(`API publique ${path}`, async () => {
    const response = await request(`${baseURL}${path}`);
    if (!(response.headers.get("content-type") || "").includes("application/json")) throw new Error("JSON attendu");
    await response.json();
  });
}

const slowest = [...timings].sort((a, b) => b.ms - a.ms).slice(0, 5);
console.log(`\nPost-deploy timings · ${slowest.map((x) => `${x.status} ${x.ms}ms ${x.url}`).join(" | ")}`);

if (failures.length) {
  console.error("\nPost-deploy smoke FAILED");
  for (const item of failures) console.error(`- ${item}`);
  process.exit(1);
}
console.log("\nPost-deploy smoke: OK");
