const { test, expect } = require("@playwright/test");

test("login charge avec une CSP nonce sans unsafe-inline pour les scripts", async ({ page }) => {
  const response = await page.goto("/login");
  expect(response).not.toBeNull();
  expect(response.status()).toBeLessThan(400);
  const csp = response.headers()["content-security-policy"] || "";
  expect(csp).toContain("script-src 'self' 'nonce-");
  expect(csp).toContain("'strict-dynamic'");
  const scriptDirective = csp.split(";").find((item) => item.trim().startsWith("script-src")) || "";
  expect(scriptDirective).not.toContain("'unsafe-inline'");
  expect(scriptDirective).not.toContain("'unsafe-eval'");
  await expect(page.locator("body")).toBeVisible();
});

test("runner statique a une CSP isolee", async ({ request }) => {
  const response = await request.get("/code-runner/index.html");
  expect(response.ok()).toBeTruthy();
  const csp = response.headers()["content-security-policy"] || "";
  expect(csp).toContain("default-src 'none'");
  expect(csp).toContain("frame-ancestors 'self'");
  expect(response.headers()["x-frame-options"]).toBe("SAMEORIGIN");
  expect(csp).toContain("https://cdn.jsdelivr.net");
});

test("la page live conserve le runner sandbox sans same-origin", async ({ request }) => {
  const source = await request.get("/code-runner/runner.js");
  expect(source.ok()).toBeTruthy();
  const text = await source.text();
  expect(text).toContain('event.source !== parent');
  expect(text).toContain('new Worker(url)');
});
